# Implementation Plan: AgriProfit Mobile Application

**Branch**: `001-mobile-app` | **Date**: 2026-02-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mobile-app/spec.md`

## Summary

Build a production-grade React Native (Expo) mobile application for AgriProfit that connects to the existing FastAPI backend (`/api/v1`) and provides all V1 features: commodity price browsing, forecasts, transport profitability comparison, inventory management, sales tracking, community forum, notifications, and admin tools. The mobile app adds offline support (MMKV queue with last-write-wins), biometric session restoration, push notifications (Expo Push via FCM/APNs), and crash reporting (Sentry). One minimal backend addition: a push token registration endpoint.

## Technical Context

**Language/Version**: TypeScript 5, React Native 0.76+ (Expo SDK 52)
**Primary Dependencies**: Expo, React Navigation 7, Zustand 5, TanStack React Query 5, Axios, react-native-mmkv, expo-secure-store, expo-local-authentication, expo-notifications, @sentry/react-native, i18next, react-native-gifted-charts
**Storage**: MMKV (offline queue + cache), SecureStore (credentials), backend PostgreSQL (unchanged)
**Testing**: Jest + @testing-library/react-native (unit/component), Detox (E2E on CI)
**Target Platform**: Android 10+ (API 29), iOS 15+
**Project Type**: Mobile + existing API backend
**Performance Goals**: <3s app launch, <3s price lookup on 4G, 60fps scrolling, <100MB cache
**Constraints**: Offline-capable, <25MB APK, works on 2GB RAM devices, intermittent 3G connectivity
**Scale/Scope**: 1,000+ concurrent users, ~30 screens, 128+ backend endpoints consumed

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No project-specific constitution defined (template only). Gate passes by default — no violations to check.

**Post-Phase 1 re-check**: Passes. Architecture is a single mobile project consuming an existing monolith API. No unnecessary complexity added.

## Project Structure

### Documentation (this feature)

```text
specs/001-mobile-app/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: setup guide
├── contracts/           # Phase 1: API contracts
│   ├── push-token-api.md
│   └── existing-api-mapping.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
backend/                          # EXISTING — minimal changes only
├── app/
│   ├── models/
│   │   └── device_push_token.py  # NEW: push token model
│   ├── notifications/
│   │   └── routes.py             # MODIFIED: add push-token endpoints
│   └── integrations/
│       └── expo_push.py          # NEW: Expo Push API client
├── alembic/versions/
│   └── xxxx_add_device_push_tokens.py  # NEW: migration
└── tests/
    └── test_push_token.py        # NEW: endpoint tests

mobile/                           # NEW — entire directory
├── App.tsx
├── app.json
├── eas.json
├── src/
│   ├── api/                      # API client + per-domain modules
│   ├── components/               # ui/, charts/, layout/, forms/
│   ├── hooks/                    # useAuth, useBiometric, useNetwork, queries/
│   ├── navigation/               # RootNavigator, AuthStack, MainTabs, per-tab stacks
│   ├── screens/                  # auth/, dashboard/, prices/, transport/, inventory/,
│   │                             # sales/, community/, notifications/, admin/, profile/
│   ├── store/                    # Zustand stores (auth, network, offlineQueue, settings)
│   ├── services/                 # secureStorage, offlineQueue, pushNotifications,
│   │                             # biometric, analytics, sentry
│   ├── i18n/                     # en.json, hi.json
│   ├── theme/                    # colors, typography, spacing
│   ├── utils/                    # formatting, validation, constants
│   └── types/                    # api, navigation, models
├── __tests__/                    # Mirrors src/ structure
└── assets/                       # images/, fonts/
```

**Structure Decision**: Mobile + existing API pattern. The `mobile/` directory is a standalone Expo project at repo root (sibling to `backend/` and `frontend/`). Backend receives 3 new files and 1 modified file for push token support. No changes to frontend.

## Complexity Tracking

No violations to justify — architecture is straightforward: single mobile project consuming existing REST API.

---

## Phase 0 — Environment Setup

**Goals**: Initialize the Expo project, install all dependencies, configure development tooling, verify backend connectivity from mobile.

**Tasks**:
1. Create Expo project at `mobile/` with TypeScript template
2. Install all dependencies (see quickstart.md for full list)
3. Configure `app.json` with app identifiers, permissions, plugins
4. Configure `eas.json` with development/preview/production build profiles
5. Set up ESLint + Prettier for mobile project
6. Create `.env` with `EXPO_PUBLIC_API_URL`
7. Create theme constants (colors, typography, spacing) matching web design system
8. Verify app launches on Android emulator and iOS simulator
9. Verify API connectivity from emulator to local backend (`/health` endpoint)

**Deliverables**: Running Expo project, verified API connectivity, theme system

**Risks**: Android emulator networking (use `10.0.2.2` for localhost). iOS simulator may need explicit `--host` on backend.

**Exit Criteria**: `npx expo start` launches app; API health check returns 200 from emulator.

---

## Phase 1 — Core Architecture Setup

**Goals**: Establish foundational layers — API client, auth interceptors, state management, navigation skeleton, offline detection.

**Tasks**:
1. **API Client** (`src/api/client.ts`):
   - Axios instance with `baseURL`, 15s timeout
   - Request interceptor: attach JWT from SecureStore
   - Response interceptor: 401 → silent token refresh, 429 → exponential backoff
   - Network error detection → set offline state
2. **Zustand Stores**:
   - `authStore`: user, tokens, isAuthenticated, biometricEnabled
   - `networkStore`: isConnected, connectionType (via NetInfo)
   - `settingsStore`: language, theme preference
   - `offlineQueueStore`: queue items, sync status
   - All stores use MMKV persist middleware
3. **React Query Setup**:
   - `QueryClient` with `staleTime: 5min`, `gcTime: 30min`
   - `onlineManager` connected to NetInfo
   - Default retry: 3 with exponential backoff
   - `QueryClientProvider` wrapping app
4. **Navigation Skeleton**:
   - `RootNavigator`: auth check → AuthStack or MainTabs
   - `AuthStack`: LoginScreen, OTPScreen, PINSetupScreen
   - `MainTabs`: Dashboard, Prices, Transport, More (bottom tabs)
   - Placeholder screens for all routes
5. **Network Monitor**:
   - NetInfo listener → update `networkStore`
   - Offline banner component (renders at top when disconnected)
6. **i18n Setup**:
   - i18next configured with en.json and hi.json (keys only, translations later)
   - Language selector in settings

**Deliverables**: Navigable app shell with auth-gated routes, API client with interceptors, state management wired, offline banner.

**Risks**: MMKV initialization can fail on some Android 10 devices — add fallback to AsyncStorage.

**Exit Criteria**: App navigates between all placeholder screens; API client successfully calls `/health`; offline banner appears when WiFi disabled.

---

## Phase 2 — Authentication + Secure Session

**Goals**: Complete OTP login flow, JWT storage, token refresh, biometric unlock, PIN fallback.

**Tasks**:
1. **Login Screen**: Phone number input (10-digit Indian format validation), "Send OTP" button
2. **OTP Screen**: 6-digit code input with auto-advance, countdown timer, resend button (with cooldown)
3. **Profile Completion Screen**: Name, state, district pickers (data from `/mandis/states` and `/mandis/districts`)
4. **Auth API Module** (`src/api/auth.ts`): requestOTP, verifyOTP, completeProfile, refreshToken, logout
5. **SecureStore Integration**: Store access_token, refresh_token, PIN hash
6. **Token Refresh**: Silent refresh in axios interceptor (already scaffolded in Phase 1)
7. **Biometric Setup**:
   - After first successful login, prompt to enable biometric unlock
   - Store biometric preference in authStore (persisted)
   - On app launch with expired token: biometric prompt → restore from SecureStore refresh token
8. **PIN Fallback**:
   - PIN setup screen (4-6 digit PIN)
   - PIN stored as hash in SecureStore
   - PIN entry screen when biometric fails or is unavailable
9. **Logout**: Clear SecureStore tokens, reset authStore, deactivate push token, navigate to login

**Deliverables**: Complete auth flow from phone number → OTP → dashboard, biometric/PIN re-auth, secure token storage.

**Risks**: OTP SMS delivery delays in rural areas — mitigated by clear retry UI and 5-minute validity. Biometric prompt can be confusing on first use — add explanatory text.

**Exit Criteria**: User can login with OTP, close and reopen app (auto-login), biometric unlock works after token expiry, PIN fallback works on devices without biometrics, logout fully clears state.

---

## Phase 3 — Core Features (Prices, Transport, Dashboard)

**Goals**: Implement the primary value screens — commodity prices, forecasts, transport comparison, and dashboard.

**Tasks**:
1. **Dashboard Screen**:
   - Top movers widget (`/prices/top-movers`)
   - Market summary (`/analytics/summary`)
   - Quick links to Prices, Transport, Inventory
   - Pull-to-refresh
2. **Commodity List Screen**:
   - FlatList with search bar (`/commodities/with-prices`)
   - Category filter chips (`/commodities/categories`)
   - Each row: commodity name, latest modal price, change indicator
   - Virtualized list for 456+ commodities
3. **Commodity Detail Screen**:
   - Price history chart (react-native-gifted-charts LineChart)
   - 7-day / 30-day toggle
   - Mandi price comparison list (sorted by price desc)
   - Forecast section with confidence indicators
   - Data from `/commodities/{id}/details`, `/forecasts/commodity/{id}`
4. **Transport Screen**:
   - Origin picker (state → district)
   - Commodity selector
   - "Compare Mandis" button → results list
   - Each result: mandi name, distance, transport cost, commodity price, net profit
   - Sort by net profit descending
5. **Chart Optimization**:
   - Lazy load chart library
   - Reduce data points on small screens (sample every Nth point)
   - Use `useMemo` for chart data transformation
6. **React Query Hooks**:
   - `useCommodities()`, `useCommodityDetail(id)`, `usePrices(commodityId)`, `useForecasts(commodityId)`
   - `useTransportCalculation()`, `useTransportComparison()`
   - Appropriate `staleTime` per query type (prices: 5min, commodities: 30min)

**Deliverables**: Fully functional prices, forecast, and transport screens with charts, search, filtering.

**Risks**: Chart rendering on low-end devices — mitigate with data point sampling and lazy loading. 456 commodities in one list — mitigate with FlatList virtualization and search-first UX.

**Exit Criteria**: User can browse commodities, view price charts with forecasts, compare transport costs to 3+ mandis. All screens load within 3 seconds on 4G.

---

## Phase 4 — Inventory, Sales, Community

**Goals**: Implement CRUD screens for inventory, sales, and the community forum.

**Tasks**:
1. **Inventory Screen**:
   - List of user's inventory items (`/inventory/`)
   - Add button → form: commodity picker, quantity, unit, storage date
   - Swipe-to-delete with confirmation
   - Market value per item (calculated from latest prices)
   - Stock summary view (`/inventory/stock`)
2. **Sales Screen**:
   - Sales history list (`/sales/`)
   - Record sale form: commodity, quantity, unit, price, buyer (optional), date
   - Sales analytics tab (`/sales/analytics`): total revenue, avg price, trends chart
3. **Community Screen**:
   - Post feed (FlatList, paginated, `/community/posts/`)
   - Post detail: content, replies, upvote button
   - Create post: title, body, post type selector
   - Reply to post
   - Upvote/remove upvote (optimistic update)
   - Delete own post (with confirmation)
   - District filter tab (posts in user's district)
4. **Form Components**:
   - Reusable form inputs with validation (react-hook-form not needed — simple controlled components for mobile)
   - Date picker (Expo DateTimePicker)
   - Commodity picker (searchable dropdown)

**Deliverables**: Working inventory CRUD, sales CRUD with analytics, community forum with posts/replies/upvotes.

**Risks**: Community post feed performance with many posts — mitigate with pagination and FlatList. Optimistic updates for upvotes may cause flicker on slow networks — mitigate with proper React Query optimistic mutation pattern.

**Exit Criteria**: User can add/view/delete inventory, record sales and view analytics, browse/create/reply/upvote community posts.

---

## Phase 5 — Notifications + Push

**Goals**: Implement in-app notification center, push notification registration, and deep linking from notifications.

**Tasks**:
1. **Backend Changes** (minimal):
   - Add `DevicePushToken` model (see data-model.md)
   - Add Alembic migration
   - Add `POST /notifications/push-token` and `DELETE /notifications/push-token` endpoints
   - Add `expo_push.py` utility for sending via Expo Push API
   - Modify notification creation to also trigger push delivery
   - Add `push_tokens` relationship to User model
2. **Mobile — Push Registration**:
   - Request notification permissions on first login
   - Get Expo push token via `expo-notifications`
   - Register token with backend (`POST /notifications/push-token`)
   - Re-register on each app launch (token may rotate)
   - Deactivate on logout (`DELETE /notifications/push-token`)
3. **Mobile — Notification Center**:
   - Notifications screen with FlatList (`/notifications/`)
   - Unread count badge on tab icon (`/notifications/unread-count`)
   - Mark read on tap, mark all read button
   - Deep link: tap notification → navigate to related content (post, commodity, etc.)
4. **Mobile — Push Handling**:
   - Foreground: show in-app toast (not OS notification)
   - Background: OS notification with tap → deep link
   - Killed state: tap notification → open app → navigate to content
5. **Admin — Broadcast**:
   - Admin broadcast screen: compose alert, select target (all users or district)
   - Uses `POST /notifications/bulk`

**Deliverables**: Push notifications working end-to-end, in-app notification center, admin broadcast.

**Risks**: Push token lifecycle management — tokens can expire or change. Mitigated by re-registering on every app launch and cleaning invalid tokens on Expo API errors.

**Exit Criteria**: Push notification received on device when backend sends alert. Tapping notification navigates to correct screen. Unread badge updates in real-time. Admin can broadcast to all or by district.

---

## Phase 6 — Offline Queue + Sync Engine

**Goals**: Implement offline data caching and write queue with automatic sync.

**Tasks**:
1. **MMKV Storage Layer**:
   - Initialize MMKV with encryption key from SecureStore
   - Cache wrapper: `get<T>(key)`, `set<T>(key, value)`, `delete(key)`, `clear()`
   - 100MB size limit enforcement with LRU eviction
2. **Read Cache** (React Query integration):
   - Configure `persister` for React Query using MMKV
   - Commodity list, prices, inventory, sales → cached on successful fetch
   - `staleTime` tuning: prices 5min, commodities 30min, inventory 1min
   - Show cached data immediately, refetch in background
3. **Write Queue**:
   - `QueuedOperation` model stored in MMKV
   - Queue operations: add to inventory, record sale, create post, reply, upvote, delete
   - Visual indicator on queued items (pending sync badge)
   - Queue processor: on connectivity restore, process FIFO with 1s delay between operations
4. **Conflict Resolution**:
   - Each queued write includes `client_timestamp`
   - On 409 or unexpected server state: last-write-wins (mobile overwrites)
   - Toast notification: "Your changes were synced. A conflicting update was overwritten."
5. **Sync Engine**:
   - Runs on: connectivity restore, app foreground, manual pull-to-refresh
   - Processes queue → invalidates React Query cache → UI updates
   - Retry with exponential backoff (max 5 retries per operation)
   - Failed operations after max retries → flagged for user attention
6. **Offline Indicator**:
   - Banner at top of screen when offline
   - Badge on queued items
   - Queue status in settings (X items pending sync)

**Deliverables**: App works fully offline for reads, queues writes, syncs automatically on reconnect.

**Risks**: Queue corruption on app crash during sync — mitigate by processing one item at a time and marking status atomically. Storage overflow — mitigate by LRU eviction and 100MB cap.

**Exit Criteria**: User can browse cached prices offline, add inventory offline, see pending badge, reconnect → items sync within 30s. Conflict toast shows when applicable.

---

## Phase 7 — Observability + Analytics

**Goals**: Crash reporting, performance monitoring, basic usage analytics.

**Tasks**:
1. **Sentry Integration**:
   - Initialize Sentry with DSN in App.tsx
   - Wrap navigation with Sentry routing instrumentation
   - Capture unhandled JS exceptions and native crashes
   - Add performance monitoring (screen load times, API call durations)
   - Set user context (user ID, role, district) on login
   - Breadcrumbs for navigation events and API calls
2. **Custom Analytics**:
   - Event buffer in MMKV (max 100 events)
   - Track: screen views, feature usage (price lookup, transport calc, sale recorded)
   - Track: session duration, login method (OTP vs biometric vs PIN)
   - Flush buffer on app background or every 5 minutes
   - V1: send as Sentry breadcrumbs; future: dedicated analytics endpoint
3. **Error Boundaries**:
   - React error boundary wrapping each navigation stack
   - Fallback UI: "Something went wrong" with retry button
   - Report error to Sentry with component stack

**Deliverables**: Sentry dashboard showing crashes, performance data, and usage patterns.

**Risks**: Sentry SDK adds ~1.5MB to bundle — acceptable tradeoff for production visibility.

**Exit Criteria**: Crashes appear in Sentry within 1 minute. Screen performance traces visible. Usage events buffered and flushed.

---

## Phase 8 — Hardening & QA

**Goals**: Performance optimization, accessibility, i18n completion, comprehensive testing, edge case handling.

**Tasks**:
1. **Performance Optimization**:
   - Profile with Flipper / React DevTools
   - Optimize FlatList renders (memoize row components, `keyExtractor`, `getItemLayout`)
   - Lazy load non-critical screens (Admin, Profile, Settings)
   - Image optimization (compress assets, use WebP)
   - Bundle size analysis — target <25MB APK
   - Memory profiling on 2GB RAM device — identify and fix leaks
2. **Hindi Translations**:
   - Complete all translation keys in `hi.json`
   - Language toggle in Settings
   - Verify RTL not needed (Hindi is LTR)
   - Test all screens in Hindi
3. **Accessibility**:
   - Add `accessibilityLabel` to all interactive elements
   - Test with TalkBack (Android) and VoiceOver (iOS)
   - Ensure minimum touch target size (44x44pt)
4. **Edge Case Testing**:
   - Network flapping (rapid connect/disconnect cycles)
   - Token expiry during active form submission
   - Duplicate push notifications (idempotent handling)
   - Back button behavior on all screens
   - Deep link handling from killed state
   - Low storage scenario (cache eviction works)
   - Rate limit recovery (429 → wait → retry → success)
5. **Automated Testing**:
   - Unit tests: stores, API client, utilities, formatting
   - Component tests: all form screens, list screens
   - Integration tests: auth flow, offline queue sync
   - Target: 70%+ code coverage
6. **Manual QA**:
   - Test on physical devices: low-end Android (2GB RAM), mid-range, iPhone SE, iPhone 14+
   - Test on 3G throttled network
   - Test with backend down (offline mode)
   - Full regression of all user stories

**Deliverables**: Optimized, translated, tested app ready for submission.

**Risks**: Low-end device testing requires physical hardware. Mitigated by Android emulator profiles with restricted RAM/CPU.

**Exit Criteria**: All user stories pass on both platforms. 70%+ test coverage. <25MB APK. <3s launch on mid-range device. No P0/P1 bugs open.

---

## Phase 9 — Production Release

**Goals**: Build production binaries, submit to app stores, monitor launch.

**Tasks**:
1. **Pre-Release**:
   - Finalize app icons, splash screen, store screenshots
   - Write app store listing (English + Hindi)
   - Privacy policy and terms of service URLs
   - Final security audit: no hardcoded secrets, SecureStore used correctly, no debug flags
2. **EAS Build**:
   - `eas build --platform all --profile production`
   - Verify production API URL in build env
   - Verify Sentry source maps uploaded
   - Test production build on physical devices
3. **App Store Submission**:
   - Google Play: Internal testing → Closed beta → Open beta → Production
   - Apple App Store: TestFlight → App Review → Release
   - Monitor for review feedback / rejection
4. **Post-Launch Monitoring**:
   - Sentry crash rate target: <1% crash-free sessions
   - Monitor push notification delivery rate
   - Monitor API error rates from mobile User-Agent
   - Set up alerts for crash rate spikes
5. **Rollout**:
   - Google Play: staged rollout (10% → 25% → 50% → 100%)
   - Apple: immediate release after approval (no staged rollout for V1)

**Deliverables**: App live on both stores, monitoring active, rollout complete.

**Risks**: App Store rejection — mitigate by pre-submission review of guidelines. First-day crash spike — mitigate by beta testing with 50+ users before full release.

**Exit Criteria**: App live on Google Play and App Store. <1% crash rate. Push delivery >90%. No critical bugs in first 48 hours.
