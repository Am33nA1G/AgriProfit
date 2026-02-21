# Research: AgriProfit Mobile Application

**Branch**: `001-mobile-app` | **Date**: 2026-02-21

## R1: Push Token Storage & Delivery

**Decision**: Add a `device_push_tokens` table and one new FastAPI endpoint (`POST /api/v1/notifications/push-token`). Backend sends push via Expo Push API (`https://exp.host/--/api/v2/push/send`).

**Rationale**: The existing Notification model handles in-app notifications but has no concept of device push tokens. Expo Push Notifications requires the backend to store per-device Expo push tokens and call the Expo Push API when a notification is created. The RefreshToken model has `device_info` but it's a free-text field — not suitable for push delivery.

**Alternatives considered**:
- Reuse `device_info` on RefreshToken: Rejected — refresh tokens are rotated/revoked, push tokens have different lifecycle.
- Store tokens only on device: Rejected — backend must initiate push delivery.
- Firebase Admin SDK directly: Rejected — Expo Push wraps FCM/APNs and simplifies token management.

## R2: Offline Queue Architecture

**Decision**: Use MMKV (via `react-native-mmkv`) for the offline queue. Each queued operation is a serialized JSON object with `id`, `type`, `endpoint`, `method`, `payload`, `timestamp`, `retryCount`. On connectivity restore, process queue FIFO with exponential backoff per item.

**Rationale**: MMKV is synchronous, fast (10x AsyncStorage), and handles up to 100MB reliably. SQLite (via expo-sqlite) was considered but adds complexity for a simple queue. AsyncStorage has known performance issues with large data.

**Alternatives considered**:
- AsyncStorage: Rejected — slow for frequent writes, 6MB default limit on Android.
- expo-sqlite: Rejected — over-engineered for a FIFO queue; adds migration complexity.
- WatermelonDB: Rejected — full ORM overkill for queue + cache.

## R3: Conflict Resolution (Last-Write-Wins)

**Decision**: Each queued write includes a `client_timestamp` (ISO 8601). On sync, the mobile client sends the request normally. If the backend returns 409 Conflict or the response indicates the resource was modified after `client_timestamp`, the client retries with force-overwrite semantics. A toast notification informs the user: "Your changes were applied. A conflicting update was overwritten."

**Rationale**: The backend currently uses standard REST (no ETag/If-Match). True conflict detection requires comparing timestamps. Since the mobile client "wins" per spec, the simplest approach is: send the write, accept the result, notify user if the response `updated_at` differs from expected.

**Alternatives considered**:
- ETag-based optimistic concurrency: Rejected — requires backend changes across all endpoints.
- Merge strategy: Rejected — over-complex for single-user-per-account pattern.

## R4: Biometric Session Restoration

**Decision**: On first successful OTP login, encrypt and store a "session restoration key" (derived from refresh token) in the device's secure enclave via `expo-secure-store`. When the refresh token expires, prompt biometric/PIN verification via `expo-local-authentication`. On success, use the stored restoration key to call `POST /auth/refresh` with a special flag, or re-request OTP silently if the key is also expired.

**Rationale**: `expo-local-authentication` provides a unified API for Face ID, Touch ID, and Android biometrics. `expo-secure-store` uses Keychain (iOS) and EncryptedSharedPreferences (Android). Together they provide hardware-backed credential storage with biometric gate.

**Alternatives considered**:
- Store raw credentials: Rejected — security risk.
- Biometric-only without PIN fallback: Rejected — excludes devices without biometric hardware.
- Always require OTP on session expiry: Rejected — high friction, SMS delivery unreliable in rural India.

## R5: State Management Architecture

**Decision**: Zustand for client-only state (auth, UI preferences, offline queue status, network status). React Query (TanStack Query) for all server-synced state (commodities, prices, inventory, sales, notifications). React Query's `staleTime` and `gcTime` provide automatic caching. Zustand persist middleware with MMKV for offline state persistence.

**Rationale**: This mirrors the web frontend's pattern (Zustand + React Query already used). React Query's cache-first + background refetch aligns perfectly with the intermittent connectivity requirement. Zustand is lightweight (~1KB) and works well on low-memory devices.

**Alternatives considered**:
- Redux Toolkit + RTK Query: Rejected — heavier bundle, different pattern from web app.
- Zustand only: Rejected — manual cache management for server data is error-prone.
- React Query only: Rejected — not suitable for client-only state (auth, network status).

## R6: Chart Library for React Native

**Decision**: `react-native-gifted-charts` for price history and analytics charts. Fallback: `victory-native` with `react-native-skia`.

**Rationale**: `react-native-gifted-charts` uses SVG rendering (lighter than Skia), supports line/bar/area charts, has good performance on low-end devices, and has no native dependencies (pure JS + react-native-svg). The web app uses Recharts which is web-only; a different library is required for RN.

**Alternatives considered**:
- `victory-native` + Skia: More powerful but heavier; Skia adds ~2MB to bundle. Good fallback if gifted-charts lacks needed chart types.
- `react-native-chart-kit`: Rejected — unmaintained, limited customization.
- `echarts-for-react-native`: Rejected — WebView-based, poor performance on low-end devices.

## R7: Navigation Architecture

**Decision**: React Navigation 7 with a nested navigator structure: Auth Stack (Login, OTP, PIN Setup) → Main Tab Navigator (Dashboard, Prices, Transport, More) → nested stacks per tab for detail screens. Admin screens gated by role check in navigator.

**Rationale**: React Navigation is the standard for Expo apps (Expo Router is an alternative but adds file-based routing complexity that doesn't benefit this project). Tab-based navigation is the standard mobile pattern for apps with 4-6 primary sections.

**Alternatives considered**:
- Expo Router (file-based): Rejected — adds unnecessary abstraction; route structure is already well-defined.
- React Navigation drawer: Rejected — tabs are more discoverable for farmers unfamiliar with mobile apps.

## R8: Internationalization (Hindi + English)

**Decision**: `i18next` + `react-i18next` with JSON translation files. Language selection stored in Zustand (persisted). RTL support not needed (Hindi is LTR).

**Rationale**: `i18next` is the de facto standard, works identically on web and mobile, supports lazy-loading namespaces (reduce bundle for unused languages), and has interpolation/pluralization built-in.

**Alternatives considered**:
- `expo-localization` only: Rejected — no runtime switching, only detects device locale.
- Custom solution: Rejected — unnecessary reinvention.

## R9: Observability Stack

**Decision**: Sentry React Native SDK for crash reporting and performance monitoring. Custom lightweight analytics module using a local event buffer that flushes to a future analytics endpoint (or Sentry breadcrumbs in V1). No third-party analytics SDK to minimize bundle size and avoid data privacy concerns.

**Rationale**: Sentry provides crash reporting, ANR detection, slow frame tracking, and network request monitoring in a single SDK. It's the most widely used crash reporter for React Native with Expo support. Custom analytics avoids adding Firebase Analytics or Mixpanel (large SDKs with privacy implications).

**Alternatives considered**:
- Firebase Crashlytics: Rejected — requires Firebase SDK which adds complexity; Sentry has better RN integration.
- Bugsnag: Viable but less Expo-native than Sentry.
- No observability: Rejected — rural users won't file bug reports; crash data is essential.

## R10: Network Connectivity Detection

**Decision**: `@react-native-community/netinfo` for connectivity detection. Zustand store tracks `isConnected` and `connectionType` (wifi/cellular/none). React Query's `onlineManager` is configured to use NetInfo, automatically pausing/resuming queries based on connectivity.

**Rationale**: NetInfo is the standard RN networking library, maintained by the community, and works with Expo. Integrating it with React Query's `onlineManager` means all server queries automatically respect connectivity without per-query logic.

**Alternatives considered**:
- Polling a health endpoint: Rejected — wasteful on metered connections.
- Manual fetch-based detection: Rejected — less reliable than native API.
