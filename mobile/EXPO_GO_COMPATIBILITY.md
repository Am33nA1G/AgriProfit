# Expo Go Compatibility Fix

## Issue
The app was using `react-native-mmkv` which requires NitroModules - not supported in Expo Go.

**Error:**
```
Error: NitroModules are not supported in Expo Go!
Use EAS (`expo prebuild`) or eject to a bare workflow instead.
```

## Solution
Implemented a **dual-storage strategy**:
- **Expo Go (development)**: Uses `@react-native-async-storage/async-storage`
- **Production builds**: Uses `react-native-mmkv` with encryption

## Changes Made

### 1. Installed AsyncStorage
```bash
npm install @react-native-async-storage/async-storage
```

### 2. Updated `mmkvStorage.ts`
- Detects if running in Expo Go
- Falls back to AsyncStorage when MMKV is unavailable
- Maintains same API for Zustand persistence

### 3. Removed `newArchEnabled` from `app.json`
- Improves Expo Go compatibility

## How It Works

```typescript
// Automatically detects environment
const isExpoGo = Platform.constants?.expoRuntimeVersion !== undefined;

if (!isExpoGo) {
  // Use MMKV (encrypted, fast)
  mmkvInstance = new MMKV({ ... });
} else {
  // Use AsyncStorage (Expo Go compatible)
  AsyncStorage = require('@react-native-async-storage/async-storage').default;
}
```

## Development vs Production

| Environment | Storage | Encryption | Speed |
|-------------|---------|------------|-------|
| **Expo Go** | AsyncStorage | None | Slower |
| **Development Build** | MMKV | AES-256 | Fast |
| **Production** | MMKV | AES-256 | Fast |

## Security Note

⚠️ **Expo Go has NO encryption** because AsyncStorage doesn't support it.
- Auth tokens are still in `expo-secure-store` (hardware-backed) ✅
- Only cache data uses AsyncStorage (market prices, settings)
- For production, build with `expo build` to get MMKV encryption

## Running the App

### Expo Go (Quick Development)
```bash
npm start
# Scan QR code with Expo Go app
```

### Development Build (Full Features)
```bash
npx expo prebuild
npm run android  # or npm run ios
```

### Production Build
```bash
npx expo build:android  # or build:ios
```

## What Works in Expo Go

✅ Login/logout
✅ Dashboard
✅ Commodities browsing
✅ Mandi search
✅ Community posts
✅ Offline queue
✅ Settings persistence

⚠️ **Limitations:**
- No MMKV encryption (cache data unencrypted)
- AsyncStorage is slower than MMKV

## Recommendation

For **serious testing**, create a development build:
```bash
npx expo install expo-dev-client
npx expo prebuild
npm run android
```

This gives you:
- ✅ MMKV with encryption
- ✅ Full native module support
- ✅ Faster performance
- ✅ Production-like environment
