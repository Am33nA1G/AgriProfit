import { useEffect, useRef } from 'react';
import { AppState } from 'react-native';
import NetInfo from '@react-native-community/netinfo';
import { useOfflineQueueStore } from '../store/offlineQueueStore';
import { processOfflineQueue } from '../services/offlineQueue';
import { queryClient } from '../api/queryClient';

/**
 * Hook that monitors connectivity and auto-syncs the offline queue
 * whenever the app comes back online.
 */
export function useOfflineQueue() {
  const { queue, isSyncing } = useOfflineQueueStore();
  const wasOfflineRef = useRef(false);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(async state => {
      const isOnline = !!state.isConnected;

      if (!isOnline) {
        wasOfflineRef.current = true;
        return;
      }

      // Just came back online
      if (wasOfflineRef.current) {
        wasOfflineRef.current = false;
        const pendingCount = useOfflineQueueStore.getState().queue.filter(
          op => op.status === 'pending' || op.status === 'failed',
        ).length;

        if (pendingCount > 0) {
          const result = await processOfflineQueue();
          if (result.synced > 0) {
            // Refresh relevant data after sync
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            queryClient.invalidateQueries({ queryKey: ['sales'] });
            queryClient.invalidateQueries({ queryKey: ['community'] });
          }
        }
      }
    });

    return unsubscribe;
  }, []);

  // Also sync when app comes to foreground
  useEffect(() => {
    const subscription = AppState.addEventListener('change', async nextState => {
      if (nextState === 'active') {
        const netInfo = await NetInfo.fetch();
        if (!netInfo.isConnected) return;

        const operations = useOfflineQueueStore.getState().queue;
        const pending = operations.filter(op => op.status === 'pending' || op.status === 'failed');

        if (pending.length > 0) {
          await processOfflineQueue();
          queryClient.invalidateQueries({ queryKey: ['inventory'] });
          queryClient.invalidateQueries({ queryKey: ['sales'] });
          queryClient.invalidateQueries({ queryKey: ['community'] });
        }
      }
    });

    return () => subscription.remove();
  }, []);

  const pendingCount = queue.filter(op => op.status === 'pending').length;
  const failedCount = queue.filter(op => op.status === 'failed').length;

  return { pendingCount, failedCount, isSyncing, queue };
}
