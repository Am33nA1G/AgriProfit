import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { mmkvStorage } from '../services/mmkvStorage';

export type QueuedOperationStatus = 'pending' | 'syncing' | 'completed' | 'failed';

export interface QueuedOperation {
  id: string;
  type: string;
  endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  payload?: unknown;
  client_timestamp: string;
  retry_count: number;
  status: QueuedOperationStatus;
  error_message?: string;
}

interface OfflineQueueState {
  queue: QueuedOperation[];
  isSyncing: boolean;
}

interface OfflineQueueActions {
  enqueue: (op: Omit<QueuedOperation, 'retry_count' | 'status'>) => void;
  dequeue: (id: string) => void;
  markSyncing: (id: string) => void;
  markFailed: (id: string, error: string) => void;
  clearCompleted: () => void;
  setIsSyncing: (value: boolean) => void;
  updateStatus: (id: string, status: QueuedOperationStatus) => void;
}

export const useOfflineQueueStore = create<OfflineQueueState & OfflineQueueActions>()(
  persist(
    set => ({
      queue: [],
      isSyncing: false,

      enqueue: op =>
        set(state => ({
          queue: [...state.queue, { ...op, retry_count: 0, status: 'pending' }],
        })),

      dequeue: id =>
        set(state => ({
          queue: state.queue.filter(op => op.id !== id),
        })),

      markSyncing: id =>
        set(state => ({
          queue: state.queue.map(op => (op.id === id ? { ...op, status: 'syncing' } : op)),
        })),

      markFailed: (id, error) =>
        set(state => ({
          queue: state.queue.map(op =>
            op.id === id
              ? {
                  ...op,
                  status: 'failed',
                  error_message: error,
                  retry_count: op.retry_count + 1,
                }
              : op,
          ),
        })),

      clearCompleted: () =>
        set(state => ({
          queue: state.queue.filter(op => op.status !== 'completed'),
        })),

      setIsSyncing: isSyncing => set({ isSyncing }),

      updateStatus: (id, status) =>
        set(state => ({
          queue: state.queue.map(op => (op.id === id ? { ...op, status } : op)),
        })),
    }),
    {
      name: 'offline-queue',
      storage: mmkvStorage,
    },
  ),
);
