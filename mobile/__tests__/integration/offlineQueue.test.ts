import { useOfflineQueueStore } from '../../src/store/offlineQueueStore';
import { enqueueOperation, processOfflineQueue } from '../../src/services/offlineQueue';

// Mock API client
jest.mock('../../src/api/client', () => ({
  __esModule: true,
  default: {
    post: jest.fn().mockResolvedValue({ data: { id: '1' } }),
    put: jest.fn().mockResolvedValue({ data: {} }),
    patch: jest.fn().mockResolvedValue({ data: {} }),
    delete: jest.fn().mockResolvedValue({}),
  },
}));

// Mock NetInfo
jest.mock('@react-native-community/netinfo', () => ({
  __esModule: true,
  default: {
    addEventListener: jest.fn().mockReturnValue(() => {}),
    fetch: jest.fn().mockResolvedValue({ isConnected: true }),
  },
}));

// Mock MMKV storage
jest.mock('../../src/services/mmkvStorage', () => ({
  mmkv: {
    getString: jest.fn().mockReturnValue(null),
    set: jest.fn(),
    delete: jest.fn(),
  },
  mmkvStorage: {
    getItem: jest.fn().mockReturnValue(null),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

beforeEach(() => {
  useOfflineQueueStore.setState({ queue: [], isSyncing: false });
  jest.clearAllMocks();
});

describe('Offline queue integration', () => {
  it('enqueues operation when called', () => {
    enqueueOperation('inventory_add', 'POST', '/inventory/', { commodity_id: '1' });

    const queue = useOfflineQueueStore.getState().queue;
    expect(queue).toHaveLength(1);
    expect(queue[0].endpoint).toBe('/inventory/');
    expect(queue[0].method).toBe('POST');
    expect(queue[0].status).toBe('pending');
  });

  it('processes pending operations and clears them', async () => {
    const apiClient = require('../../src/api/client').default;

    enqueueOperation('inventory_add', 'POST', '/inventory/', { commodity_id: '1' });
    enqueueOperation('sale_add', 'POST', '/sales/', { commodity_id: '1', quantity: 5 });

    expect(useOfflineQueueStore.getState().queue).toHaveLength(2);

    const result = await processOfflineQueue();

    expect(result.synced).toBe(2);
    expect(result.failed).toBe(0);
    expect(apiClient.post).toHaveBeenCalledTimes(2);
    // Completed operations should be cleared
    expect(useOfflineQueueStore.getState().queue).toHaveLength(0);
  });

  it('marks operations as failed when API throws', async () => {
    const apiClient = require('../../src/api/client').default;
    apiClient.post.mockRejectedValueOnce(new Error('Network error'));

    enqueueOperation('inventory_add', 'POST', '/inventory/', {});

    const result = await processOfflineQueue();

    expect(result.synced).toBe(0);
    expect(result.failed).toBe(1);

    const queue = useOfflineQueueStore.getState().queue;
    expect(queue).toHaveLength(1);
    expect(queue[0].status).toBe('failed');
    expect(queue[0].retry_count).toBe(1);
  });

  it('processes operations in FIFO order', async () => {
    const apiClient = require('../../src/api/client').default;
    const callOrder: string[] = [];

    apiClient.post.mockImplementation((endpoint: string) => {
      callOrder.push(endpoint);
      return Promise.resolve({ data: {} });
    });

    enqueueOperation('op1', 'POST', '/endpoint-1', {});
    enqueueOperation('op2', 'POST', '/endpoint-2', {});
    enqueueOperation('op3', 'POST', '/endpoint-3', {});

    await processOfflineQueue();

    expect(callOrder).toEqual(['/endpoint-1', '/endpoint-2', '/endpoint-3']);
  });

  it('skips operations that exceeded max retries', async () => {
    const { OFFLINE_QUEUE_MAX_RETRIES } = require('../../src/utils/constants');
    const id = 'max-retry-op';

    useOfflineQueueStore.setState({
      queue: [{
        id,
        type: 'test',
        endpoint: '/test',
        method: 'POST',
        payload: {},
        client_timestamp: new Date().toISOString(),
        retry_count: OFFLINE_QUEUE_MAX_RETRIES,
        status: 'failed',
      }],
      isSyncing: false,
    });

    const apiClient = require('../../src/api/client').default;
    const result = await processOfflineQueue();

    expect(result.failed).toBe(1);
    expect(apiClient.post).not.toHaveBeenCalled();
  });
});
