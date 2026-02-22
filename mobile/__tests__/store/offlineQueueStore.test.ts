import { act } from 'react-test-renderer';
import { useOfflineQueueStore } from '../../src/store/offlineQueueStore';

const makeOp = (overrides = {}) => ({
  id: 'test-id-' + Math.random(),
  type: 'inventory',
  endpoint: '/inventory/',
  method: 'POST' as const,
  payload: { commodity_id: '1', quantity: 10 },
  client_timestamp: new Date().toISOString(),
  ...overrides,
});

beforeEach(() => {
  useOfflineQueueStore.setState({ queue: [], isSyncing: false });
});

describe('offlineQueueStore', () => {
  it('enqueue adds operation with pending status', () => {
    const op = makeOp();
    act(() => {
      useOfflineQueueStore.getState().enqueue(op);
    });

    const queue = useOfflineQueueStore.getState().queue;
    expect(queue).toHaveLength(1);
    expect(queue[0].status).toBe('pending');
    expect(queue[0].retry_count).toBe(0);
    expect(queue[0].id).toBe(op.id);
  });

  it('dequeue removes operation by id', () => {
    const op = makeOp({ id: 'remove-me' });
    act(() => {
      useOfflineQueueStore.getState().enqueue(op);
    });
    expect(useOfflineQueueStore.getState().queue).toHaveLength(1);

    act(() => {
      useOfflineQueueStore.getState().dequeue('remove-me');
    });
    expect(useOfflineQueueStore.getState().queue).toHaveLength(0);
  });

  it('markSyncing updates status to syncing', () => {
    const op = makeOp({ id: 'sync-me' });
    act(() => {
      useOfflineQueueStore.getState().enqueue(op);
      useOfflineQueueStore.getState().markSyncing('sync-me');
    });

    const item = useOfflineQueueStore.getState().queue.find(o => o.id === 'sync-me');
    expect(item?.status).toBe('syncing');
  });

  it('markFailed increments retry_count and sets error', () => {
    const op = makeOp({ id: 'fail-me' });
    act(() => {
      useOfflineQueueStore.getState().enqueue(op);
      useOfflineQueueStore.getState().markFailed('fail-me', 'Network error');
    });

    const item = useOfflineQueueStore.getState().queue.find(o => o.id === 'fail-me');
    expect(item?.status).toBe('failed');
    expect(item?.retry_count).toBe(1);
    expect(item?.error_message).toBe('Network error');
  });

  it('clearCompleted removes completed operations', () => {
    const op1 = makeOp({ id: 'op1' });
    const op2 = makeOp({ id: 'op2' });
    act(() => {
      useOfflineQueueStore.getState().enqueue(op1);
      useOfflineQueueStore.getState().enqueue(op2);
      useOfflineQueueStore.getState().updateStatus('op1', 'completed');
    });

    expect(useOfflineQueueStore.getState().queue).toHaveLength(2);

    act(() => {
      useOfflineQueueStore.getState().clearCompleted();
    });

    const queue = useOfflineQueueStore.getState().queue;
    expect(queue).toHaveLength(1);
    expect(queue[0].id).toBe('op2');
  });

  it('setIsSyncing updates isSyncing flag', () => {
    act(() => {
      useOfflineQueueStore.getState().setIsSyncing(true);
    });
    expect(useOfflineQueueStore.getState().isSyncing).toBe(true);

    act(() => {
      useOfflineQueueStore.getState().setIsSyncing(false);
    });
    expect(useOfflineQueueStore.getState().isSyncing).toBe(false);
  });

  it('maintains FIFO order for queue', () => {
    const ops = ['a', 'b', 'c'].map(id => makeOp({ id }));
    act(() => {
      ops.forEach(op => useOfflineQueueStore.getState().enqueue(op));
    });

    const ids = useOfflineQueueStore.getState().queue.map(o => o.id);
    expect(ids).toEqual(['a', 'b', 'c']);
  });
});
