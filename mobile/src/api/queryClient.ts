import { QueryClient } from '@tanstack/react-query';
import { onlineManager } from '@tanstack/react-query';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';
import { persistQueryClient } from '@tanstack/react-query-persist-client';
import NetInfo from '@react-native-community/netinfo';
import { mmkv } from '../services/mmkvStorage';

// Connect React Query online manager to NetInfo
onlineManager.setEventListener(setOnline => {
  return NetInfo.addEventListener(state => {
    setOnline(!!state.isConnected);
  });
});

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 30 * 60 * 1000, // 30 minutes
      retry: 3,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 0,
    },
  },
});

// Persist query cache to MMKV for offline access
const mmkvStorageAdapter = {
  getItem: (key: string) => mmkv.getString(key) ?? null,
  setItem: (key: string, value: string) => mmkv.set(key, value),
  removeItem: (key: string) => mmkv.delete(key),
};

const persister = createSyncStoragePersister({
  storage: mmkvStorageAdapter,
  key: 'rq-cache',
  throttleTime: 1000,
  // Limit cache size to ~2MB
  serialize: data => {
    const serialized = JSON.stringify(data);
    if (serialized.length > 2 * 1024 * 1024) {
      // Trim oldest queries if cache too large
      return JSON.stringify({
        ...data,
        clientState: {
          ...data.clientState,
          queries: data.clientState.queries.slice(-50),
        },
      });
    }
    return serialized;
  },
});

persistQueryClient({
  queryClient,
  persister,
  maxAge: 24 * 60 * 60 * 1000, // 24 hours
  buster: '1',
});
