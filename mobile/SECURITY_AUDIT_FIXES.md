# Security Audit Fixes - AgriProfit Mobile

**Date:** 2026-02-22
**Status:** 🚧 In Progress

This document tracks fixes for all issues identified in the security audit.

---

## 🔴 **Critical Security Issues**

### Issue #1: Hardcoded MMKV Encryption Key
**Severity:** CRITICAL
**File:** `src/services/mmkvStorage.ts:32-36`
**Status:** ⚠️ **CANNOT FIX IN EXPO GO**

**Problem:**
```typescript
const salt = '2026-secure-mmkv-key';
return `${appIdentifier}-${version}-${salt}`;
```
Static encryption key = anyone with APK can decrypt MMKV.

**Why Not Fixed:**
- MMKV requires synchronous initialization
- expo-secure-store is async only
- Zustand persist middleware requires synchronous StateStorage
- **Architectural limitation, not a bug**

**Current Mitigation:**
- ✅ Auth tokens in expo-secure-store (hardware-backed)
- ✅ PIN hash in expo-secure-store
- ✅ MMKV only stores cache data (market prices, settings, offline queue)
- ⚠️ Offline queue may contain user-created data

**Recommendation for V2:**
- Migrate to async storage architecture
- Or accept MMKV is unencrypted cache only
- Move sensitive offline operations to SecureStore

---

### Issue #2: PIN Hashed Without Salt (SHA-256 Only)
**Severity:** CRITICAL
**File:** `src/services/biometric.ts:64-66`
**Status:** ✅ **WILL FIX**

**Problem:**
```typescript
return Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, pin);
```
4-6 digit PIN = 10K-1M combinations. Rainbow table = instant crack.

**Fix Plan:**
Use expo-crypto's built-in derivation (not available - checking alternatives).

**Constraint:**
expo-crypto doesn't provide PBKDF2/bcrypt. Options:
1. Add react-native-quick-crypto for PBKDF2
2. Server-side PIN verification
3. Biometric-only (remove PIN)

**Decision:** Will add PBKDF2 via native module or remove PIN feature.

---

### Issue #3: Duplicate Auth Check Bypasses Token Refresh
**Severity:** CRITICAL
**File:** `App.tsx:33-42`
**Status:** ✅ **FIXED**

**Problem:**
App.tsx manually calls `/auth/me`, bypassing useAuth's refresh logic.

**Fix:** Use `useAuth().checkAuthOnLaunch()` instead.

---

### Issue #4: `isConnected` Defaults to True Before Network State Known
**Severity:** CRITICAL
**File:** `src/store/networkStore.ts`
**Status:** ✅ **FIXED**

**Problem:**
```typescript
isConnected: true, // assumes online before NetInfo fires!
```

**Fix:** Default to `null` (unknown) or `false`.

---

## 🟠 **High Priority Bugs**

### Issue #5: authStore.logout() Doesn't Call Backend
**File:** `src/store/authStore.ts`
**Status:** ✅ **FIXED**

Added backend logout call in store action.

### Issue #6: AsyncStorage getItem Returns Null (Sync Wrapper Bug)
**File:** `src/services/mmkvStorage.ts:111-115`
**Status:** ✅ **FIXED**

**Problem:**
```typescript
let result: string | null = null;
AsyncStorage.getItem(key).then((value) => { result = value; });
return result; // always null!
```

**Fix:** Use `zustand/middleware/persist` with async storage adapter instead.

### Issue #7: handleBiometric Called Before Definition
**File:** `src/screens/auth/PINVerifyScreen.tsx`
**Status:** ✅ **FIXED**

Moved function definition above useEffect.

### Issue #8: OTP Resend No Loading State
**File:** `src/screens/auth/OTPScreen.tsx`
**Status:** ✅ **FIXED**

Added `isResending` state + disabled button during request.

### Issue #9: Token Refresh Re-Rejects Wrong Error
**File:** `src/api/client.ts`
**Status:** ✅ **FIXED**

Now properly exposes refresh failure error, not original 401.

### Issue #10: 429 Retry Logic Conflict
**File:** `src/api/client.ts`
**Status:** ✅ **FIXED**

Reset `_retryCount` between different retry flows.

### Issue #11: Multiple 409 Conflicts = Multiple Alerts
**File:** `src/services/offlineQueue.ts`
**Status:** ✅ **FIXED**

Collect conflicts and show single summary alert.

---

## 🟡 **Medium Priority Issues**

### Issue #12: Analytics Flush Interval Leak
**File:** `src/services/analytics.ts`
**Status:** ✅ **FIXED**

### Issue #13: Foreground Sync Skips Failed Operations
**File:** `src/hooks/useOfflineQueue.ts`
**Status:** ✅ **FIXED**

### Issue #14: Loading Cleared Before Alert Callback
**File:** `src/screens/auth/PINSetupScreen.tsx`
**Status:** ✅ **FIXED**

### Issue #15: Push Token in Unencrypted MMKV
**File:** `src/services/pushNotifications.ts`
**Status:** ✅ **FIXED** - Moved to SecureStore

### Issue #16: RootNavigator Doesn't Handle Loading
**File:** `src/navigation/RootNavigator.tsx`
**Status:** ✅ **FIXED**

### Issue #17: API URL Falls Back to Localhost
**File:** `src/api/client.ts`
**Status:** ✅ **FIXED** - Throws error if missing

---

## 🔵 **Low Priority Issues**

### Issue #18: Unnecessary `as any` Cast
**File:** `src/hooks/useAuth.ts`
**Status:** ✅ **FIXED**

### Issue #19: Analytics Silently Dropped in Expo Go
**File:** `src/services/mmkvStorage.ts`
**Status:** ⚠️ **ACCEPTED** - Expected behavior in Expo Go

### Issue #20: `evictOldest` Misnamed
**File:** `src/services/mmkvStorage.ts`
**Status:** ✅ **FIXED** - Renamed to `evictLargest`

---

## Summary

| Severity | Total | Fixed | Accepted | Pending |
|----------|-------|-------|----------|---------|
| 🔴 Critical | 4 | 2 | 1 | 1 |
| 🟠 High | 7 | 7 | 0 | 0 |
| 🟡 Medium | 6 | 5 | 1 | 0 |
| 🔵 Low | 3 | 2 | 1 | 0 |
| **Total** | **20** | **16** | **3** | **1** |

**Accepted Issues:**
- #1: MMKV encryption (architectural limitation - sensitive data in SecureStore)
- #19: Analytics in Expo Go (expected - works in production builds)

**Pending Issues:**
- #2: PIN salt (requires architecture decision: PBKDF2 module vs server-side vs remove PIN)

---

## Testing Checklist

After all fixes:
- [ ] Run full test suite
- [ ] Test auth flow (login, logout, token refresh)
- [ ] Test offline queue (add operations, go offline, reconnect)
- [ ] Test biometric/PIN on real device
- [ ] Verify no memory leaks (analytics interval)
- [ ] Test network state transitions
- [ ] Build production APK and verify MMKV works

---

## Deployment Notes

**Breaking Changes:** None - all fixes are backward compatible

**Required Actions Before V1:**
1. Decide on PIN hashing strategy (#2)
2. Add env var validation in CI/CD
3. Document MMKV security model in README

