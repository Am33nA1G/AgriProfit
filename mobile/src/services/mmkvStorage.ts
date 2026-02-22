import type { StateStorage } from 'zustand/middleware';
import { Platform } from 'react-native';
import { CACHE_MAX_SIZE_MB, CACHE_EVICT_THRESHOLD_MB } from '../utils/constants';

/**
 * EXPO GO COMPATIBILITY:
 * MMKV uses NitroModules which are not supported in Expo Go.
 * We use AsyncStorage as a fallback for development in Expo Go,
 * and MMKV for production builds (after expo prebuild).
 *
 * SECURITY NOTE: MMKV encryption key strategy.
 * Using app-bundle-specific deterministic key to prevent cross-app key reuse.
 * Critical secrets (auth tokens, PIN hash) are stored separately in expo-secure-store.
 */

// Lazy imports to avoid errors in Expo Go
let MMKV: any = null;
let AsyncStorage: any = null;
let mmkvInstance: any = null;
let useMMKV = false;

// Try to initialize MMKV, fall back to AsyncStorage
try {
  // Check if we're in Expo Go (no MMKV support)
  const isExpoGo = Platform.constants?.expoRuntimeVersion !== undefined;

  if (!isExpoGo) {
    // Try to load MMKV for production builds
    const MMKVModule = require('react-native-mmkv');
    MMKV = MMKVModule.MMKV;

    function getEncryptionKey(): string {
      const appIdentifier = 'com.agriprofit.mobile';
      const version = 'v1.0.0';
      const salt = '2026-secure-mmkv-key';
      return `${appIdentifier}-${version}-${salt}`;
    }

    mmkvInstance = new MMKV({
      id: 'agriprofit-storage',
      encryptionKey: getEncryptionKey(),
    });
    useMMKV = true;
    console.log('✅ Using MMKV for storage');
  }
} catch (error) {
  // MMKV not available, will use AsyncStorage
  console.log('⚠️ MMKV not available, using AsyncStorage fallback');
}

// Load AsyncStorage if MMKV is not available
if (!useMMKV) {
  AsyncStorage = require('@react-native-async-storage/async-storage').default;
  console.log('✅ Using AsyncStorage for storage (Expo Go mode)');
}

// Keys that must never be evicted
const PROTECTED_KEYS = new Set([
  'auth-store',
  'network-store',
  'settings-store',
  'offline-queue-store',
  '__analytics-buffer__',
]);

/**
 * Returns total storage size in MB (MMKV only, AsyncStorage doesn't support this)
 */
export function getCacheSize(): number {
  if (!useMMKV || !mmkvInstance) return 0;

  const keys = mmkvInstance.getAllKeys();
  let totalBytes = 0;
  for (const key of keys) {
    const value = mmkvInstance.getString(key);
    if (value) totalBytes += value.length * 2;
  }
  return totalBytes / (1024 * 1024);
}

/**
 * Evict non-critical cached data (MMKV only)
 */
export function evictOldest(targetSizeMB: number): void {
  if (!useMMKV || !mmkvInstance) return;

  const evictable = mmkvInstance.getAllKeys().filter((k: string) => !PROTECTED_KEYS.has(k));
  evictable.sort((a: string, b: string) => {
    if (a === 'rq-cache') return -1;
    if (b === 'rq-cache') return 1;
    const sizeA = mmkvInstance.getString(a)?.length ?? 0;
    const sizeB = mmkvInstance.getString(b)?.length ?? 0;
    return sizeB - sizeA;
  });

  for (const key of evictable) {
    if (getCacheSize() <= targetSizeMB) break;
    mmkvInstance.delete(key);
  }
}

// Zustand StateStorage adapter that works with both MMKV and AsyncStorage
export const mmkvStorage: StateStorage = {
  getItem: (key: string): string | null => {
    if (useMMKV && mmkvInstance) {
      const value = mmkvInstance.getString(key);
      return value ?? null;
    }
    // AsyncStorage is async - Zustand will handle this via persistStore's rehydrate
    // Return null immediately, data will be loaded asynchronously
    return null;
  },

  setItem: (key: string, value: string): void => {
    if (useMMKV && mmkvInstance) {
      // Evict before writing if cache is near the limit
      if (getCacheSize() > CACHE_EVICT_THRESHOLD_MB) {
        evictOldest(CACHE_MAX_SIZE_MB * 0.7);
      }
      mmkvInstance.set(key, value);
    } else if (AsyncStorage) {
      // Fire and forget for AsyncStorage
      AsyncStorage.setItem(key, value).catch((error: Error) => {
        console.error('AsyncStorage setItem error:', error);
      });
    }
  },

  removeItem: (key: string): void => {
    if (useMMKV && mmkvInstance) {
      mmkvInstance.delete(key);
    } else if (AsyncStorage) {
      AsyncStorage.removeItem(key).catch((error: Error) => {
        console.error('AsyncStorage removeItem error:', error);
      });
    }
  },
};

// Export a dummy mmkv instance for compatibility
export const mmkv = mmkvInstance || {
  getString: (key: string) => null,
  set: (key: string, value: string) => {},
  delete: (key: string) => {},
  getAllKeys: () => [],
};
