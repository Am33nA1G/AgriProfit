import { Alert } from 'react-native';
import * as Sentry from '@sentry/react-native';
import { useOfflineQueueStore, QueuedOperation } from '../store/offlineQueueStore';
import apiClient from '../api/client';
import { OFFLINE_QUEUE_MAX_RETRIES } from '../utils/constants';

/**
 * Process the offline queue, replaying each pending operation in FIFO order.
 * Called when the app comes back online.
 */
export async function processOfflineQueue(): Promise<{ synced: number; failed: number }> {
  const store = useOfflineQueueStore.getState();
  const { queue, setIsSyncing, markSyncing, updateStatus, markFailed, clearCompleted } = store;

  const pending = queue.filter(op => op.status === 'pending' || op.status === 'failed');

  if (pending.length === 0) return { synced: 0, failed: 0 };

  const transaction = Sentry.startTransaction({
    name: 'offline_queue_sync',
    op: 'queue.process',
    data: { pending_count: pending.length },
  });

  setIsSyncing(true);
  const startTime = Date.now();
  let synced = 0;
  let failed = 0;
  const conflicts: string[] = [];

  for (const op of pending) {
    if (op.retry_count >= OFFLINE_QUEUE_MAX_RETRIES) {
      markFailed(op.id, 'Max retries exceeded');
      failed++;
      continue;
    }

    markSyncing(op.id);

    try {
      await replayOperation(op);
      updateStatus(op.id, 'completed');
      synced++;
    } catch (err: unknown) {
      const httpStatus = (err as any)?.response?.status;
      if (httpStatus === 409) {
        // Conflict: server version wins — mark completed, collect for single alert
        updateStatus(op.id, 'completed');
        synced++;
        conflicts.push(op.type || 'operation');
      } else {
        const message = err instanceof Error ? err.message : 'Unknown error';
        markFailed(op.id, message);
        failed++;
      }
    }
  }

  // Show single alert for all conflicts
  if (conflicts.length > 0) {
    Alert.alert(
      'Sync Conflicts',
      `${conflicts.length} offline change(s) could not be applied because they conflict with more recent updates. The latest versions have been kept.`,
      [{ text: 'OK' }],
    );
  }

  clearCompleted();
  setIsSyncing(false);

  transaction.setData('synced', synced);
  transaction.setData('failed', failed);
  transaction.setData('duration_ms', Date.now() - startTime);
  transaction.finish();

  return { synced, failed };
}

async function replayOperation(op: QueuedOperation): Promise<void> {
  switch (op.method) {
    case 'POST':
      await apiClient.post(op.endpoint, op.payload);
      break;
    case 'PUT':
      await apiClient.put(op.endpoint, op.payload);
      break;
    case 'PATCH':
      await apiClient.patch(op.endpoint, op.payload);
      break;
    case 'DELETE':
      await apiClient.delete(op.endpoint);
      break;
    default:
      throw new Error(`Unsupported method: ${op.method}`);
  }
}

/**
 * Enqueue an offline operation with a unique ID.
 */
export function enqueueOperation(
  type: string,
  method: QueuedOperation['method'],
  endpoint: string,
  payload?: unknown,
): void {
  const id = `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  useOfflineQueueStore.getState().enqueue({
    id,
    type,
    method,
    endpoint,
    payload,
    client_timestamp: new Date().toISOString(),
  });
}
