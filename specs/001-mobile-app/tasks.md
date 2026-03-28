# Tasks: AgriProfit Mobile Application

**Input**: Design documents from `/specs/001-mobile-app/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize Expo project, install dependencies, configure tooling

- [X] T001 Create Expo project at `mobile/` using `npx create-expo-app mobile --template expo-template-blank-typescript`
- [X] T002 Install core Expo dependencies: expo-secure-store, expo-local-authentication, expo-notifications, expo-constants, expo-device, expo-linking, expo-status-bar, @react-native-community/netinfo, react-native-mmkv in `mobile/`
- [X] T003 [P] Install navigation dependencies: @react-navigation/native, @react-navigation/bottom-tabs, @react-navigation/native-stack, react-native-screens, react-native-safe-area-context in `mobile/`
- [X] T004 [P] Install state and data dependencies: zustand, @tanstack/react-query, axios in `mobile/`
- [X] T005 [P] Install UI dependencies: react-native-svg, react-native-gifted-charts, react-native-gesture-handler, react-native-reanimated in `mobile/`
- [X] T006 [P] Install i18n and observability dependencies: i18next, react-i18next, @sentry/react-native in `mobile/`
- [X] T007 [P] Install dev dependencies: typescript, @types/react, jest, @testing-library/react-native in `mobile/`
- [X] T008 Configure `mobile/app.json` with bundleIdentifier (com.agriprofit.mobile), Android package, permissions (RECEIVE_BOOT_COMPLETED, VIBRATE), plugins (sentry, expo-notifications, expo-secure-store, expo-local-authentication), iOS infoPlist (NSFaceIDUsageDescription)
- [X] T009 [P] Configure `mobile/eas.json` with development (developmentClient, internal), preview (internal, staging API URL), and production (production API URL) build profiles
- [X] T010 [P] Configure ESLint and Prettier for `mobile/` with TypeScript rules matching project conventions
- [X] T011 [P] Create `mobile/.env` with EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1, EXPO_PUBLIC_SENTRY_DSN, EXPO_PUBLIC_ENV=development
- [X] T012 Create theme constants: `mobile/src/theme/colors.ts` (green primary matching web palette), `mobile/src/theme/typography.ts` (font sizes 12-32), `mobile/src/theme/spacing.ts` (4px base scale)
- [X] T013 [P] Create TypeScript type definitions for all API response shapes in `mobile/src/types/models.ts` (User, Commodity, PriceRecord, Mandi, Forecast, InventoryItem, SaleRecord, CommunityPost, CommunityReply, Notification, TransportCalculation) per data-model.md
- [X] T014 [P] Create TypeScript type definitions for navigation params in `mobile/src/types/navigation.ts` (RootStackParamList, AuthStackParamList, MainTabParamList, PricesStackParamList, CommunityStackParamList, AdminStackParamList)
- [X] T015 [P] Create TypeScript type definitions for API request/response wrappers in `mobile/src/types/api.ts` (PaginatedResponse<T>, ApiError, AuthTokens, OTPRequest, OTPVerify)
- [X] T016 Create utility functions: `mobile/src/utils/formatting.ts` (formatPrice with INR symbol and commas, formatDate to DD MMM YYYY, formatRelativeTime), `mobile/src/utils/validation.ts` (validatePhoneNumber regex ^[6-9][0-9]{9}$, validateOTP 6-digit check), `mobile/src/utils/constants.ts` (API_TIMEOUT=15000, MAX_RETRY=3, OTP_LENGTH=6, OTP_EXPIRY_SECONDS=300)
- [ ] T017 
**Checkpoint**: Expo project initialized, all dependencies installed, types defined, theme configured.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: API client, state management, navigation shell, network detection — MUST complete before any user story

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T018 Create Axios API client in `mobile/src/api/client.ts` with baseURL from EXPO_PUBLIC_API_URL, 15s timeout, Content-Type: application/json header, request interceptor that reads access_token from SecureStore and attaches as Bearer header
- [X] T019 Add response interceptor to `mobile/src/api/client.ts` for 401 handling: read refresh_token from SecureStore, call POST /auth/refresh, store new tokens, retry original request; on refresh failure call authStore.logout()
- [X] T020 Add response interceptor to `mobile/src/api/client.ts` for 429 handling: read retry-after header (default 5s), wait, retry original request with max 3 retries using exponential backoff (2^attempt * 1000ms)
- [X] T021 Create Zustand auth store in `mobile/src/store/authStore.ts` with state: user (User|null), isAuthenticated (boolean), biometricEnabled (boolean), isLoading (boolean); actions: setUser, setTokens (writes to SecureStore), logout (clears SecureStore + resets state), checkAuth (reads SecureStore on app launch)
- [X] T022 [P] Create Zustand network store in `mobile/src/store/networkStore.ts` with state: isConnected (boolean), connectionType (string); initialize with NetInfo.addEventListener that updates state on connectivity changes
- [X] T023 [P] Create Zustand settings store in `mobile/src/store/settingsStore.ts` with state: language ('en'|'hi'), theme ('light'|'dark'); persist to MMKV using zustand/middleware persist with MMKV storage adapter
- [X] T024 [P] Create Zustand offline queue store in `mobile/src/store/offlineQueueStore.ts` with state: queue (QueuedOperation[]), isSyncing (boolean); actions: enqueue(op), dequeue(id), markSyncing(id), markFailed(id, error), clearCompleted(); persist to MMKV
- [X] T025 Create MMKV storage adapter for Zustand persist in `mobile/src/services/mmkvStorage.ts`: initialize MMKV instance with encryption key from SecureStore, export getItem/setItem/removeItem functions matching Zustand StateStorage interface
- [X] T026 Create SecureStore wrapper in `mobile/src/services/secureStorage.ts` with functions: saveTokens(access, refresh), getAccessToken(), getRefreshToken(), clearTokens(), savePinHash(hash), getPinHash(), saveBiometricPreference(enabled), getBiometricPreference()
- [X] T027 Configure React Query client in `mobile/src/api/queryClient.ts`: create QueryClient with defaultOptions staleTime=5*60*1000 (5min), gcTime=30*60*1000 (30min), retry=3, retryDelay=exponentialBackoff; connect onlineManager to NetInfo using onlineManager.setEventListener
- [X] T028 Create i18n configuration in `mobile/src/i18n/index.ts`: initialize i18next with react-i18next, set fallback to 'en', load from `mobile/src/i18n/en.json` and `mobile/src/i18n/hi.json`; create placeholder JSON files with top-level keys: common, auth, prices, transport, inventory, sales, community, notifications, admin
- [X] T029 Create RootNavigator in `mobile/src/navigation/RootNavigator.tsx`: check authStore.isAuthenticated on mount, render AuthStack if not authenticated, MainTabs if authenticated; wrap with NavigationContainer
- [X] T030 Create AuthStack navigator in `mobile/src/navigation/AuthStack.tsx` with screens: LoginScreen, OTPScreen, ProfileCompleteScreen, PINSetupScreen (all as native-stack screens)
- [X] T031 Create MainTabs bottom tab navigator in `mobile/src/navigation/MainTabs.tsx` with 5 tabs: Dashboard (home icon), Prices (trending-up icon), Transport (truck icon), More (menu icon); conditionally show Admin tab if user.role === 'admin'
- [X] T032 [P] Create PricesStack navigator in `mobile/src/navigation/PricesStack.tsx` with screens: CommodityListScreen, CommodityDetailScreen, MandiDetailScreen
- [X] T033 [P] Create CommunityStack navigator in `mobile/src/navigation/CommunityStack.tsx` with screens: PostsScreen, PostDetailScreen, CreatePostScreen
- [X] T034 [P] Create MoreStack navigator in `mobile/src/navigation/MoreStack.tsx` with screens: MoreMenuScreen, InventoryScreen, AddInventoryScreen, SalesScreen, AddSaleScreen, CommunityStack, NotificationsScreen, ProfileScreen, SettingsScreen
- [X] T035 Create placeholder screens for all navigation routes: `mobile/src/screens/auth/LoginScreen.tsx`, `OTPScreen.tsx`, `ProfileCompleteScreen.tsx`, `PINSetupScreen.tsx`; `mobile/src/screens/dashboard/DashboardScreen.tsx`; `mobile/src/screens/prices/CommodityListScreen.tsx`, `CommodityDetailScreen.tsx`; `mobile/src/screens/transport/TransportScreen.tsx`; plus all remaining screens as simple View with screen name text
- [X] T036 Create reusable UI components: `mobile/src/components/ui/Button.tsx` (primary/secondary/outline variants, loading state), `mobile/src/components/ui/Card.tsx` (shadow, padding), `mobile/src/components/ui/Input.tsx` (label, error message, phone number mask), `mobile/src/components/ui/LoadingSpinner.tsx`, `mobile/src/components/ui/EmptyState.tsx` (icon, message, action button)
- [X] T037 [P] Create layout components: `mobile/src/components/layout/Screen.tsx` (SafeAreaView wrapper with padding, optional scroll), `mobile/src/components/layout/OfflineBanner.tsx` (reads networkStore.isConnected, shows yellow banner "You are offline" when disconnected), `mobile/src/components/layout/Header.tsx` (title, back button, optional right action)
- [X] T038 Wire App.tsx entry point in `mobile/App.tsx`: wrap with QueryClientProvider, initialize i18n, initialize Sentry (placeholder DSN), render RootNavigator, add OfflineBanner overlay, call authStore.checkAuth on mount
- [ ] T039 Verify complete navigation flow: app launches → shows LoginScreen → can navigate to all placeholder screens → OfflineBanner appears when WiFi disabled on emulator

**Checkpoint**: Foundation ready — API client with interceptors, state management, navigation shell, offline detection all working. User story implementation can begin.

---

## Phase 3: User Story 1 — Phone-Based Login (Priority: P1) MVP

**Goal**: Farmer can authenticate via OTP, store tokens securely, auto-login on app restart, and logout.

**Independent Test**: Enter phone number → receive OTP → enter OTP → see dashboard. Close app → reopen → auto-logged in. Tap logout → returns to login.

### Implementation for User Story 1

- [X] T040 [US1] Create auth API module in `mobile/src/api/auth.ts` with functions: requestOTP(phoneNumber: string) → POST /auth/request-otp, verifyOTP(phoneNumber: string, otp: string) → POST /auth/verify-otp (returns AuthTokens + User), completeProfile(data: {name, state, district}) → POST /auth/complete-profile, refreshToken(refreshToken: string) → POST /auth/refresh, logout() → POST /auth/logout, getCurrentUser() → GET /auth/me
- [X] T041 [US1] Implement LoginScreen in `mobile/src/screens/auth/LoginScreen.tsx`: phone number input with +91 prefix display, validation (10 digits starting with 6-9), "Send OTP" button with loading state, error display for invalid number or network failure, disable button during API call
- [X] T042 [US1] Implement OTPScreen in `mobile/src/screens/auth/OTPScreen.tsx`: 6 individual digit inputs with auto-advance on entry, auto-submit when all 6 digits entered, countdown timer (300s) with "Resend OTP" button enabled after cooldown (30s), error message on incorrect OTP, max 3 attempts tracking, loading state during verification
- [X] T043 [US1] Implement ProfileCompleteScreen in `mobile/src/screens/auth/ProfileCompleteScreen.tsx`: name input, state dropdown (data from GET /mandis/states), district dropdown (data from GET /mandis/districts?state=X, reloads on state change), "Save" button that calls completeProfile API, navigate to MainTabs on success; skip if user.is_profile_complete is already true
- [X] T044 [US1] Implement auth flow orchestration in `mobile/src/hooks/useAuth.ts`: login(phone, otp) function that calls verifyOTP → saves tokens to SecureStore via secureStorage.saveTokens → updates authStore → navigates to ProfileComplete or Dashboard; checkAuthOnLaunch() that reads tokens from SecureStore, validates access token by calling GET /auth/me, refreshes if expired, sets authStore state
- [X] T045 [US1] Implement silent token refresh in auth flow: in useAuth.checkAuthOnLaunch(), if access token call fails with 401, try refreshToken(); if refresh succeeds update tokens in SecureStore; if refresh fails, clear state and show login screen
- [X] T046 [US1] Implement logout in `mobile/src/hooks/useAuth.ts`: call POST /auth/logout on backend (fire-and-forget, don't block on failure), clear all SecureStore tokens, reset authStore, reset React Query cache (queryClient.clear()), navigate to AuthStack
- [X] T047 [US1] Create basic DashboardScreen in `mobile/src/screens/dashboard/DashboardScreen.tsx`: display "Welcome, {user.name}" header, show 3 quick action cards (Check Prices, Calculate Transport, View Inventory) that navigate to respective screens, pull-to-refresh that invalidates all React Query caches
- [X] T048 [US1] Add OTP input component in `mobile/src/components/forms/OTPInput.tsx`: row of 6 TextInput boxes, each accepts 1 digit, auto-advance focus to next box on input, backspace moves to previous box, paste support for 6-digit string, exposes onChange(code: string) callback when all digits filled

**Checkpoint**: User can login with OTP, auto-login on app restart, logout. Dashboard shows welcome message. This is the MVP — all other features build on this.

---

## Phase 4: User Story 2 — Browse Commodity Prices (Priority: P1)

**Goal**: Farmer can browse commodities, view price history charts, compare mandi prices, and see forecasts.

**Independent Test**: Navigate to Prices tab → see commodity list → tap commodity → see price chart + mandi comparison + forecasts. Search works. Toggle 7d/30d works.

### Implementation for User Story 2

- [X] T049 [P] [US2] Create commodities API module in `mobile/src/api/commodities.ts` with functions: getCommoditiesWithPrices(page, limit, category?) → GET /commodities/with-prices, getCommodityDetail(id) → GET /commodities/{id}/details, getCategories() → GET /commodities/categories, searchCommodities(query) → GET /commodities/search/?q=
- [X] T050 [P] [US2] Create prices API module in `mobile/src/api/prices.ts` with functions: getHistoricalPrices(commodityId, days?) → GET /prices/historical, getCurrentPrices() → GET /prices/current, getTopMovers() → GET /prices/top-movers, getPricesForCommodity(commodityId) → GET /prices/commodity/{id}
- [X] T051 [P] [US2] Create forecasts API module in `mobile/src/api/forecasts.ts` with functions: getForecastsForCommodity(commodityId) → GET /forecasts/commodity/{id}
- [X] T052 [US2] Create React Query hooks in `mobile/src/hooks/queries/useCommodities.ts`: useCommoditiesWithPrices(page, category) with staleTime 5min and keepPreviousData for pagination, useCommodityDetail(id) with staleTime 5min, useCategories() with staleTime 30min, useSearchCommodities(query) with enabled: query.length >= 2
- [X] T053 [P] [US2] Create React Query hooks in `mobile/src/hooks/queries/usePrices.ts`: useHistoricalPrices(commodityId, days) with staleTime 5min, useTopMovers() with staleTime 5min
- [X] T054 [P] [US2] Create React Query hooks in `mobile/src/hooks/queries/useForecasts.ts`: useForecasts(commodityId) with staleTime 10min
- [X] T055 [US2] Create PriceChart component in `mobile/src/components/charts/PriceChart.tsx`: accepts priceHistory array (PriceRecord[]) and days (7|30), renders LineChart from react-native-gifted-charts with price_modal on Y axis and price_date on X axis, formats Y axis as INR, formats X axis as short date, handles empty data with "No price data" message, memoize data transformation with useMemo
- [X] T056 [US2] Implement CommodityListScreen in `mobile/src/screens/prices/CommodityListScreen.tsx`: FlatList rendering commodities from useCommoditiesWithPrices, each row shows commodity name, category badge, latest modal price (formatted INR), price change indicator (up/down arrow with green/red), search bar at top that calls useSearchCommodities, horizontal scrolling category filter chips from useCategories, pull-to-refresh, loading skeleton on first load, pagination via onEndReached
- [X] T057 [US2] Implement CommodityDetailScreen in `mobile/src/screens/prices/CommodityDetailScreen.tsx`: receives commodityId from navigation params, uses useCommodityDetail hook, renders: commodity name + category header, PriceChart component with 7d/30d toggle buttons, "Mandi Prices" section with FlatList of mandis sorted by price_modal descending (each row: mandi name, district, price, date), "Forecast" section showing 7-day and 30-day predicted prices with confidence percentage, pull-to-refresh
- [X] T058 [US2] Add cached data display to CommodityListScreen: when offline (networkStore.isConnected === false), React Query serves from cache automatically; add visual indicator "Showing cached data" text below search bar when isConnected is false and data.isStale is true
- [X] T059 [US2] Optimize CommodityListScreen for 456+ items: use getItemLayout for fixed-height rows (60px), memoize renderItem with React.memo, set windowSize={5} and maxToRenderPerBatch={10} on FlatList, add initialNumToRender={20}
- [X] T060 [US2] Update DashboardScreen in `mobile/src/screens/dashboard/DashboardScreen.tsx`: add "Top Movers" horizontal scroll section using useTopMovers hook, showing top 5 gainers and top 5 losers as small cards with commodity name, price, and change percentage

**Checkpoint**: Farmer can browse 456 commodities, search, filter by category, view price charts, compare mandi prices, and see forecasts. Works offline with cached data.

---

## Phase 5: User Story 3 — Transport Cost & Profitability (Priority: P2)

**Goal**: Farmer can calculate transport costs and compare net profitability across mandis.

**Independent Test**: Navigate to Transport → select origin + commodity → see mandis ranked by net profit with cost breakdown.

### Implementation for User Story 3

- [X] T061 [P] [US3] Create transport API module in `mobile/src/api/transport.ts` with functions: calculateCost(origin, destination, commodityId, quantity) → POST /transport/calculate, compareMandis(origin, commodityId, mandis[]) → POST /transport/compare, getVehicleTypes() → GET /transport/vehicles, getDistricts() → GET /transport/districts
- [X] T062 [US3] Create React Query hooks in `mobile/src/hooks/queries/useTransport.ts`: useTransportCompare as useMutation (POST), useVehicleTypes() with staleTime 1hr, useTransportDistricts() with staleTime 1hr
- [X] T063 [US3] Implement TransportScreen in `mobile/src/screens/transport/TransportScreen.tsx`: origin picker (state dropdown → district dropdown using data from GET /mandis/states and /mandis/districts), commodity picker (searchable dropdown using commodities list), quantity input (numeric), "Compare Mandis" button that triggers useTransportCompare mutation, results section: FlatList of mandis sorted by net_profit descending, each row shows mandi name, distance_km, transport_cost (INR), commodity_price (INR), net_profit (INR, bold green/red), loading state during calculation, empty state if no results
- [X] T064 [US3] Create reusable picker components: `mobile/src/components/forms/StatePicker.tsx` (dropdown populated from /mandis/states), `mobile/src/components/forms/DistrictPicker.tsx` (dropdown populated from /mandis/districts?state=X, resets on state change), `mobile/src/components/forms/CommodityPicker.tsx` (searchable list with commodity name + category)

**Checkpoint**: Farmer can compare transport costs to multiple mandis and see which gives best net profit.

---

## Phase 6: User Story 4 — Inventory Management (Priority: P2)

**Goal**: Farmer can add, view, and delete inventory entries with market value.

**Independent Test**: Navigate to Inventory → add entry → see in list with market value → delete entry → gone from list.

### Implementation for User Story 4

- [X] T065 [P] [US4] Create inventory API module in `mobile/src/api/inventory.ts` with functions: getInventory() → GET /inventory/, addInventory(data: {commodity_id, quantity, unit}) → POST /inventory/, updateInventory(id, data) → PUT /inventory/{id}, deleteInventory(id) → DELETE /inventory/{id}, getStock() → GET /inventory/stock, analyzeInventory() → POST /inventory/analyze
- [X] T066 [US4] Create React Query hooks in `mobile/src/hooks/queries/useInventory.ts`: useInventory() with staleTime 1min, useAddInventory as useMutation with onSuccess invalidating inventory query, useDeleteInventory as useMutation with optimistic update (remove from cache immediately, rollback on error), useInventoryStock() with staleTime 5min
- [X] T067 [US4] Implement InventoryScreen in `mobile/src/screens/inventory/InventoryScreen.tsx`: FlatList of inventory items from useInventory, each row shows commodity name, quantity + unit, storage date, estimated market value (INR), swipe-to-delete using Swipeable from react-native-gesture-handler with red "Delete" action and confirmation Alert.alert, "Add" FAB button navigating to AddInventoryScreen, pull-to-refresh, empty state "No inventory items yet"
- [X] T068 [US4] Implement AddInventoryScreen in `mobile/src/screens/inventory/AddInventoryScreen.tsx`: CommodityPicker (reuse from T064), quantity numeric input, unit picker (quintal, kg, ton), storage date picker (default today), "Save" button calling useAddInventory mutation, navigate back on success, loading state during save, validation: quantity > 0, commodity selected

**Checkpoint**: Farmer can manage inventory with real-time market valuations.

---

## Phase 7: User Story 5 — Sales Tracking (Priority: P2)

**Goal**: Farmer can record sales and view analytics (revenue, average price, trends).

**Independent Test**: Navigate to Sales → record sale → see in history → view analytics tab with totals.

### Implementation for User Story 5

- [X] T069 [P] [US5] Create sales API module in `mobile/src/api/sales.ts` with functions: getSales() → GET /sales/, addSale(data: {commodity_id, quantity, unit, sale_price, buyer_name?, sale_date}) → POST /sales/, updateSale(id, data) → PUT /sales/{id}, deleteSale(id) → DELETE /sales/{id}, getSalesAnalytics() → GET /sales/analytics
- [X] T070 [US5] Create React Query hooks in `mobile/src/hooks/queries/useSales.ts`: useSales() with staleTime 1min, useAddSale as useMutation with onSuccess invalidating sales + analytics queries, useDeleteSale as useMutation with optimistic update, useSalesAnalytics() with staleTime 5min
- [X] T071 [US5] Implement SalesScreen in `mobile/src/screens/sales/SalesScreen.tsx`: two tabs (History | Analytics), History tab: FlatList of sales from useSales, each row shows commodity name, quantity, sale price (INR), date, buyer name if present; "Record Sale" FAB navigating to AddSaleScreen; Analytics tab: total revenue card, total sales count, average price per commodity list, simple bar chart of monthly revenue using react-native-gifted-charts BarChart; pull-to-refresh on both tabs
- [X] T072 [US5] Implement AddSaleScreen in `mobile/src/screens/sales/AddSaleScreen.tsx`: CommodityPicker, quantity numeric input, unit picker, sale price input (INR), buyer name input (optional), sale date picker (default today), "Record Sale" button calling useAddSale mutation, navigate back on success, validation: quantity > 0, price > 0, commodity selected

**Checkpoint**: Farmer can track sales with full analytics.

---

## Phase 8: User Story 6 — Community Forum (Priority: P3)

**Goal**: Farmer can browse, create, reply to, upvote, and delete own community posts.

**Independent Test**: Browse posts → create post → see it in feed → reply → upvote another post → delete own post.

### Implementation for User Story 6

- [X] T073 [P] [US6] Create community API module in `mobile/src/api/community.ts` with functions: getPosts(page, type?, district?) → GET /community/posts/, getPost(id) → GET /community/posts/{id}, createPost(data: {title, content, post_type, district?}) → POST /community/posts/, deletePost(id) → DELETE /community/posts/{id}, getReplies(postId) → GET /community/posts/{id}/replies, addReply(postId, content) → POST /community/posts/{id}/reply, upvotePost(postId) → POST /community/posts/{id}/upvote, removeUpvote(postId) → DELETE /community/posts/{id}/upvote, searchPosts(query) → GET /community/posts/search?q=
- [X] T074 [US6] Create React Query hooks in `mobile/src/hooks/queries/useCommunity.ts`: usePosts(page, type, district) with staleTime 2min, usePost(id) with staleTime 2min, useCreatePost as useMutation invalidating posts, useDeletePost as useMutation with optimistic remove, useReplies(postId) with staleTime 1min, useAddReply as useMutation invalidating replies, useUpvotePost as useMutation with optimistic increment of upvote_count
- [X] T075 [US6] Implement PostsScreen in `mobile/src/screens/community/PostsScreen.tsx`: FlatList of posts from usePosts, each row shows title, author name, timestamp (relative), upvote count, reply count, post_type badge (discussion/question/tip/alert); filter tabs (All, My District, Questions, Tips, Alerts); "New Post" FAB navigating to CreatePostScreen; pull-to-refresh; pagination via onEndReached
- [X] T076 [US6] Implement PostDetailScreen in `mobile/src/screens/community/PostDetailScreen.tsx`: post header (title, author, timestamp, type badge), post content body, upvote button (filled if user has upvoted, calls useUpvotePost/removeUpvote), delete button (visible only if post.user_id === current user, calls useDeletePost with confirmation alert), replies section as FlatList from useReplies, reply input bar at bottom (TextInput + Send button calling useAddReply)
- [X] T077 [US6] Implement CreatePostScreen in `mobile/src/screens/community/CreatePostScreen.tsx`: title input (required, max 200 chars), content TextInput (multiline, required), post_type picker (discussion, question, tip), district auto-filled from user.district (editable), "Post" button calling useCreatePost, navigate back on success, validation: title and content required

**Checkpoint**: Community forum fully functional with posts, replies, upvotes.

---

## Phase 9: User Story 7 — Notifications & Push (Priority: P3)

**Goal**: Farmer receives push notifications and can view/manage them in-app.

**Independent Test**: Backend sends alert → push notification arrives on device → tap opens notification center → mark as read → badge updates.

### Backend Tasks (Push Token Infrastructure)

- [X] T078 [US7] Create DevicePushToken SQLAlchemy model in `backend/app/models/device_push_token.py` per data-model.md: id (UUID PK), user_id (FK users.id CASCADE), expo_push_token (String 255), device_platform (String 10, check ios/android), device_model (String 100 nullable), app_version (String 20 nullable), is_active (Boolean default true), created_at, updated_at; UniqueConstraint on (user_id, expo_push_token)
- [X] T079 [US7] Create Alembic migration in `backend/alembic/versions/` for device_push_tokens table: create table, add index idx_push_tokens_user_active on (user_id, is_active), add index idx_push_tokens_token on (expo_push_token); run `alembic revision --autogenerate -m "add_device_push_tokens"`
- [X] T080 [US7] Add push_tokens relationship to User model in `backend/app/models/user.py`: add `push_tokens: Mapped[list["DevicePushToken"]] = relationship("DevicePushToken", back_populates="user", cascade="all, delete-orphan")`
- [X] T081 [US7] Create Pydantic schemas in `backend/app/notifications/push_schemas.py`: PushTokenRegister (expo_push_token: str with regex validation for ExponentPushToken pattern, device_platform: Literal['ios','android'], device_model: str|None, app_version: str|None), PushTokenResponse (id, expo_push_token, device_platform, is_active, created_at/updated_at), PushTokenDeactivate (expo_push_token: str)
- [X] T082 [US7] Add push token endpoints to `backend/app/notifications/routes.py`: POST /push-token (auth required, upsert on user_id+expo_push_token, return 201 for new or 200 for update), DELETE /push-token (auth required, set is_active=false for matching token, return 200)
- [X] T083 [US7] Create Expo Push API utility in `backend/app/integrations/expo_push.py`: async function send_push_notifications(tokens: list[str], title: str, body: str, data: dict|None) that POSTs to https://exp.host/--/api/v2/push/send with httpx, handles DeviceNotRegistered errors by deactivating invalid tokens in DB, returns ticket IDs
- [X] T084 [US7] Integrate push delivery into notification creation: modify `backend/app/notifications/routes.py` POST /notifications/ and POST /notifications/bulk to also call send_push_notifications for all active push tokens of target user(s) after creating in-app notification
- [X] T085 [US7] Add push token registration tests in `backend/tests/test_push_token.py`: test register new token (201), test update existing token (200), test deactivate token (200), test invalid token format (422), test unauthenticated (401)

### Mobile Tasks (Notifications)

- [X] T086 [P] [US7] Create notifications API module in `mobile/src/api/notifications.ts` with functions: getNotifications(page, isRead?) → GET /notifications/, getUnreadCount() → GET /notifications/unread-count, markRead(id) → PUT /notifications/{id}/read, markAllRead() → PUT /notifications/read-all, deleteNotification(id) → DELETE /notifications/{id}, registerPushToken(token, platform, model?, appVersion?) → POST /notifications/push-token, deactivatePushToken(token) → DELETE /notifications/push-token
- [X] T087 [US7] Create push notification service in `mobile/src/services/pushNotifications.ts`: registerForPushNotifications() that requests permissions via Notifications.requestPermissionsAsync(), gets Expo push token via Notifications.getExpoPushTokenAsync(), calls registerPushToken API, stores token locally in MMKV; setupNotificationHandlers() that configures foreground handler (show in-app toast, don't show OS notification), background/tap handler (navigate to relevant screen based on data.type and data.target_id)
- [X] T088 [US7] Create React Query hooks in `mobile/src/hooks/queries/useNotifications.ts`: useNotifications(page, isRead) with staleTime 1min, useUnreadCount() with staleTime 30s and refetchInterval 60s (polling for badge), useMarkRead as useMutation with optimistic update (set is_read=true in cache, decrement unread count), useMarkAllRead as useMutation invalidating all notification queries
- [X] T089 [US7] Implement NotificationsScreen in `mobile/src/screens/notifications/NotificationsScreen.tsx`: FlatList of notifications from useNotifications, each row shows title (bold if unread), message preview (1 line), relative timestamp, notification_type icon; tap marks as read and navigates: price_alert → CommodityDetail, community → PostDetail, system/announcement → in-place expand; "Mark All Read" button in header; swipe-to-delete; unread count badge on tab icon using useUnreadCount
- [X] T090 [US7] Wire push registration into auth flow: in `mobile/src/hooks/useAuth.ts` login() function, after successful auth call registerForPushNotifications(); in logout() call deactivatePushToken(); in App.tsx on mount call setupNotificationHandlers(); re-register token on each app foreground event using AppState listener

**Checkpoint**: Push notifications delivered end-to-end, in-app notification center with badge, deep linking from notifications.

---

## Phase 10: User Story 8 — Admin Management (Priority: P3)

**Goal**: Admin users can broadcast alerts, delete any post, and view platform stats.

**Independent Test**: Login as admin → see Admin tab → broadcast alert → see in notifications → delete a post → view stats.

### Implementation for User Story 8

- [X] T091 [P] [US8] Create admin API module in `mobile/src/api/admin.ts` with functions: getStats() → GET /admin/stats, getUsers(search?) → GET /admin/users, getPosts(search?) → GET /admin/posts, deletePost(id) → DELETE /admin/posts/{id}, banUser(id) → PUT /admin/users/{id}/ban, createNotification(data) → POST /notifications/, bulkNotifications(data) → POST /notifications/bulk
- [X] T092 [US8] Create React Query hooks in `mobile/src/hooks/queries/useAdmin.ts`: useAdminStats() with staleTime 5min, useAdminUsers(search) with staleTime 2min, useAdminPosts(search) with staleTime 2min, useAdminDeletePost as useMutation, useAdminBroadcast as useMutation (calls bulkNotifications)
- [X] T093 [US8] Create AdminStack navigator in `mobile/src/navigation/AdminStack.tsx` with screens: AdminDashboardScreen, BroadcastScreen, AdminUsersScreen, AdminPostsScreen
- [X] T094 [US8] Implement AdminDashboardScreen in `mobile/src/screens/admin/AdminDashboardScreen.tsx`: stat cards from useAdminStats (total users, total posts, active commodities, data freshness), navigation buttons to Broadcast, Manage Users, Manage Posts
- [X] T095 [US8] Implement BroadcastScreen in `mobile/src/screens/admin/BroadcastScreen.tsx`: title input, message input (multiline), target picker (All Users | Specific District with district dropdown), "Send Broadcast" button calling useAdminBroadcast mutation, success confirmation toast
- [X] T096 [US8] Implement AdminPostsScreen in `mobile/src/screens/admin/AdminPostsScreen.tsx`: FlatList from useAdminPosts with search bar, each row shows title, author, date, type; swipe-to-delete on any post (admin privilege) calling useAdminDeletePost with confirmation

**Checkpoint**: Admin can manage the platform from mobile.

---

## Phase 11: Offline Engine & Sync Queue

**Purpose**: Offline data caching, write queue, and automatic sync — cross-cutting across all user stories

- [X] T097 Create offline queue engine in `mobile/src/services/offlineQueue.ts`: processQueue() function that reads queue from offlineQueueStore, processes FIFO with 1s delay between operations, for each item: set status='syncing', call apiClient with item.method/endpoint/payload, on success set status='completed' and dequeue, on 409/conflict set status='completed' with conflict toast, on network error increment retry_count and set status='pending', on max retries (5) set status='failed' with error_message; call processQueue on: NetInfo connectivity restore, app foreground (AppState), manual pull-to-refresh
- [X] T098 Create useOfflineQueue hook in `mobile/src/hooks/useOfflineQueue.ts`: enqueueOperation(type, endpoint, method, payload) that creates QueuedOperation with UUID id, client_timestamp (new Date().toISOString()), adds to offlineQueueStore; wraps each mutation in user stories: check networkStore.isConnected, if offline enqueue and show toast "Saved offline, will sync when connected", if online execute normally
- [X] T099 Integrate offline queue with inventory mutations: modify useAddInventory and useDeleteInventory in `mobile/src/hooks/queries/useInventory.ts` to use enqueueOperation when offline, update local cache optimistically, show "pending sync" badge on queued items in InventoryScreen
- [X] T100 Integrate offline queue with sales mutations: modify useAddSale in `mobile/src/hooks/queries/useSales.ts` to use enqueueOperation when offline, update local cache optimistically
- [X] T101 Integrate offline queue with community mutations: modify useCreatePost, useAddReply, useUpvotePost in `mobile/src/hooks/queries/useCommunity.ts` to use enqueueOperation when offline
- [X] T102 Add queue status indicator: create `mobile/src/components/layout/SyncStatus.tsx` that reads offlineQueueStore, shows "X items pending sync" badge in settings or profile screen, shows sync progress indicator during processQueue
- [X] T103 Add conflict resolution toast: when processQueue detects a conflict (409 response or updated_at mismatch), show toast via a toast library or Alert: "Your changes were synced. A conflicting update was overwritten." with "View Details" action (optional, shows original vs overwritten)
- [X] T104 Configure React Query persistence: create MMKV-based persister in `mobile/src/api/queryPersister.ts` that serializes React Query cache to MMKV on mutations/updates, restores cache on app launch; set maxAge to 24 hours; configure in queryClient with `persistQueryClient`
- [X] T105 Implement cache size management in `mobile/src/services/mmkvStorage.ts`: add getCacheSize() function, add evictOldest(targetSizeMB) function that removes oldest entries by timestamp until cache is under 100MB, call evictOldest before each write if cache exceeds 90MB

**Checkpoint**: App works fully offline for reads, queues writes, syncs on reconnect, handles conflicts.

---

## Phase 12: Biometric Session Restore

**Purpose**: Biometric unlock and PIN fallback for session restoration

- [X] T106 Create biometric service in `mobile/src/services/biometric.ts`: checkBiometricAvailability() returns {compatible, enrolled, available} from LocalAuthentication.hasHardwareAsync() + isEnrolledAsync(), authenticateWithBiometric() calls LocalAuthentication.authenticateAsync with promptMessage "Unlock AgriProfit", disableDeviceFallback: true; returns boolean
- [X] T107 Implement PINSetupScreen in `mobile/src/screens/auth/PINSetupScreen.tsx`: 4-6 digit PIN entry with confirm step (enter PIN, then re-enter to confirm must match), stores SHA-256 hash of PIN via secureStorage.savePinHash(), called after first successful OTP login, navigation: PIN setup → Dashboard
- [X] T108 Create PIN verification screen in `mobile/src/screens/auth/PINVerifyScreen.tsx`: 4-6 digit input, compare hash with stored hash from secureStorage.getPinHash(), 3 attempts max, on success restore session, on failure redirect to OTP login
- [X] T109 Implement session restoration flow in `mobile/src/hooks/useAuth.ts` checkAuthOnLaunch(): 1) Try access token → GET /auth/me → if success, done. 2) Try refresh token → POST /auth/refresh → if success, update tokens, done. 3) Check biometricEnabled in authStore → if true, prompt biometric via authenticateWithBiometric() → if success, try refresh token again (may have been valid but access expired) → if still fails, fall to step 4. 4) Show PINVerifyScreen → on PIN success, try refresh → if still fails, show OTP login. 5) All else fails → OTP login screen.
- [X] T110 Add biometric enrollment prompt: after first successful OTP login (in useAuth.login()), check biometricAvailability, if available show Alert "Enable fingerprint/face unlock?" → yes: set authStore.biometricEnabled=true via secureStorage.saveBiometricPreference(true), navigate to PINSetupScreen → no: navigate to PINSetupScreen (PIN is always required as fallback)

**Checkpoint**: Returning users can unlock with fingerprint/face or PIN without OTP.

---

## Phase 13: Observability & Monitoring

**Purpose**: Crash reporting, performance monitoring, usage analytics

- [X] T111 Initialize Sentry in `mobile/src/services/sentry.ts`: call Sentry.init with DSN from EXPO_PUBLIC_SENTRY_DSN, tracesSampleRate: 0.2 (20% of transactions), enable reactNativeTracingIntegration with routingInstrumentation from React Navigation, set environment from EXPO_PUBLIC_ENV, set release from Constants.expoConfig.version
- [X] T112 Wire Sentry into App.tsx: wrap App component with Sentry.wrap(), pass navigation ref to Sentry routing instrumentation for automatic screen tracking, set user context (user.id, user.role, user.district) in authStore subscriber (on login/logout)
- [X] T113 [P] Create React error boundary in `mobile/src/components/layout/ErrorBoundary.tsx`: catches render errors, calls Sentry.captureException with componentStack, renders fallback UI with "Something went wrong" message and "Try Again" button that resets error state; wrap each navigation stack with this boundary
- [X] T114 [P] Create analytics service in `mobile/src/services/analytics.ts`: trackScreen(screenName) called on navigation state change, trackEvent(name, properties?) for feature usage (price_lookup, transport_calc, sale_recorded, inventory_added, post_created), trackSession(duration) on app background; buffer events in MMKV array (max 100), flush as Sentry breadcrumbs every 5 minutes or on app background via AppState listener
- [X] T115 Add performance monitoring: add Sentry.startTransaction for key operations in API client (API call duration), chart rendering (wrap PriceChart mount with performance span), offline queue sync (total sync time); tag transactions with connection_type from networkStore

**Checkpoint**: Crashes visible in Sentry within 1 min, screen performance traces, usage analytics buffered.

---

## Phase 14: Testing & QA

**Purpose**: Automated tests for critical paths, manual QA on devices

- [X] T116 Write unit tests for auth store in `mobile/__tests__/store/authStore.test.ts`: test setUser, test logout clears state, test checkAuth with valid/expired/missing tokens (mock SecureStore)
- [X] T117 [P] Write unit tests for offline queue store in `mobile/__tests__/store/offlineQueueStore.test.ts`: test enqueue, dequeue, markSyncing, markFailed, clearCompleted, persistence to MMKV
- [X] T118 [P] Write unit tests for API client interceptors in `mobile/__tests__/api/client.test.ts`: test 401 triggers token refresh and retries, test 429 triggers backoff and retries, test network error sets offline state
- [X] T119 [P] Write unit tests for utility functions in `mobile/__tests__/utils/formatting.test.ts`: test formatPrice with various amounts (0, 100, 1500.50, 100000), test formatDate with various dates, test validatePhoneNumber with valid/invalid numbers
- [X] T120 Write component tests for LoginScreen in `mobile/__tests__/screens/auth/LoginScreen.test.tsx`: test renders phone input, test validates 10-digit number starting with 6-9, test shows error for invalid number, test disables button during loading
- [X] T121 [P] Write component tests for OTPInput in `mobile/__tests__/components/forms/OTPInput.test.tsx`: test renders 6 inputs, test auto-advance on digit entry, test backspace moves to previous, test calls onChange with complete code
- [X] T122 Write integration test for auth flow in `mobile/__tests__/integration/authFlow.test.ts`: mock API calls, test login flow end-to-end (phone → OTP → dashboard), test auto-login on app restart, test logout clears state
- [X] T123 [P] Write integration test for offline queue in `mobile/__tests__/integration/offlineQueue.test.ts`: mock NetInfo as offline, enqueue operations, mock NetInfo as online, verify queue processes, verify API calls made in order
- [ ] T124 Manual QA: test on physical low-end Android device (2GB RAM, Android 10) — verify app launches <3s, FlatList scrolls at 60fps, charts render without ANR, memory stays under 200MB during use
- [ ] T125 Manual QA: test on 3G throttled network — verify prices load <3s, OTP flow completes <60s, offline indicator appears immediately on disconnect, queued items sync within 30s of reconnect
- [ ] T126 Manual QA: test edge cases — rapid network toggle (WiFi on/off 5 times in 10s), token expiry during form submission, back button from every screen, deep link from killed state, duplicate push notifications (send same alert twice, verify idempotent)

**Checkpoint**: 70%+ code coverage on critical paths, all edge cases verified on physical devices.

---

## Phase 15: CI/CD & Release Pipeline

**Purpose**: Automated builds, testing, and app store submission

- [X] T127 Create GitHub Actions workflow in `.github/workflows/mobile-ci.yml`: trigger on push to mobile/** paths, steps: checkout, setup Node 20, install deps (npm ci in mobile/), run linter (eslint), run tests (jest --coverage), fail if coverage < 70%
- [X] T128 [P] Create EAS build workflow in `.github/workflows/mobile-build.yml`: trigger on push to main or manual dispatch, steps: checkout, setup Node 20, install EAS CLI, run `eas build --platform all --profile preview --non-interactive`, upload artifacts
- [X] T129 Configure EAS Submit in `mobile/eas.json` submit section: add iOS (appleId, ascAppId), Android (serviceAccountKeyPath for Google Play service account JSON), test submission with `eas submit --platform android --profile production`
- [ ] T130 Create app store assets: icon (1024x1024 PNG), adaptive icon (foreground + background), splash screen (matching web branding), 5 store screenshots per platform (login, prices, transport, community, dashboard), write app description (English + Hindi)

**Checkpoint**: CI runs tests on every PR, EAS builds production binaries, store assets ready.

---

## Phase 16: Production Hardening & Release

**Purpose**: Final optimization, security audit, and production deployment

- [ ] T131 Bundle size optimization: run `npx expo export --dump-sourcemap`, analyze with source-map-explorer, identify and lazy-load heavy screens (Admin, Analytics), verify APK < 25MB, remove unused dependencies
- [ ] T132 [P] Memory optimization: profile on 2GB RAM device with Flipper, identify components not unmounting (check useEffect cleanup), verify FlatList unmounts off-screen items, reduce image sizes, limit MMKV cache to 100MB with eviction
- [X] T133 [P] Chart rendering optimization: in PriceChart component, sample data points to max 30 on screen (if history has 365 points, show every 12th), use requestAnimationFrame for chart animations, test on low-end device — chart must render in <500ms
- [ ] T134 Complete Hindi translations in `mobile/src/i18n/hi.json`: translate all keys in every namespace (auth, prices, transport, inventory, sales, community, notifications, admin, common), verify all screens display correctly in Hindi, test language toggle in Settings persists via settingsStore
- [ ] T135 Security audit checklist: verify no hardcoded secrets in codebase (grep for API keys, tokens), verify SecureStore used for all sensitive data (tokens, PIN hash), verify no console.log in production build (strip with babel plugin), verify HTTPS-only API calls in production env, verify biometric prompt cannot be bypassed programmatically
- [X] T136 [P] Add rate limit handling UX: when 429 is received and retry is in progress, show non-blocking "Fetching data, please wait..." indicator at bottom of screen; after max retries failed, show "Service is busy. Please try again in a few minutes." with retry button
- [ ] T137 Create production build: run `eas build --platform all --profile production`, verify production API URL in build, verify Sentry source maps uploaded (sentry-expo plugin), test production build on physical devices (both platforms)
- [ ] T138 Submit to Google Play: upload AAB to Play Console, create internal testing track, invite 10+ testers, collect feedback for 48 hours, promote to production with staged rollout (10% → 50% → 100%)
- [ ] T139 Submit to Apple App Store: upload IPA via EAS Submit, create TestFlight build, invite 10+ testers, collect feedback, submit for App Review, release on approval
- [ ] T140 Post-launch monitoring setup: configure Sentry alerts for crash rate > 1%, monitor push notification delivery rate in Expo dashboard, create backend dashboard filter for User-Agent containing "AgriProfit" to track mobile-specific API errors

**Checkpoint**: App live on both stores, <1% crash rate, push delivery >90%, no critical bugs in first 48 hours.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion — BLOCKS all user stories
- **Phases 3-10 (User Stories)**: All depend on Phase 2 completion
  - US1 (Phase 3) → MVP, should complete first
  - US2 (Phase 4) → depends on US1 (auth required)
  - US3-5 (Phases 5-7) → depend on US1, can run in parallel with US2
  - US6 (Phase 8) → depends on US1, can run in parallel with US2-5
  - US7 (Phase 9) → depends on US1, requires backend tasks (T078-T085) first
  - US8 (Phase 10) → depends on US1 + US7 (admin needs notification system)
- **Phase 11 (Offline)**: Depends on US1 + at least US4 or US5 (needs mutations to queue)
- **Phase 12 (Biometric)**: Depends on US1 (auth flow must exist)
- **Phase 13 (Observability)**: Can start after Phase 2, runs parallel with user stories
- **Phase 14 (Testing)**: Depends on Phases 3-12 (tests cover implemented features)
- **Phase 15 (CI/CD)**: Can start after Phase 1, runs parallel with development
- **Phase 16 (Hardening)**: Depends on all prior phases complete

### Within Each User Story

- API module before React Query hooks
- React Query hooks before screens
- Reusable components before screens that use them
- Core implementation before integration/polish

### Parallel Opportunities

- All tasks marked [P] within a phase can run simultaneously
- Phases 4-8 (US2-US6) can run in parallel after US1 completes (if team capacity allows)
- Phase 13 (Observability) runs parallel with feature development
- Phase 15 (CI/CD) runs parallel with everything after Phase 1
- Backend tasks (T078-T085) can run parallel with mobile Phases 3-8

---

## Parallel Example: After Foundational Phase

```
Developer A: Phase 3 (US1 Auth) → Phase 12 (Biometric)
Developer B: Phase 9 backend tasks (T078-T085) → Phase 9 mobile tasks (T086-T090)
Developer C: Phase 4 (US2 Prices) → Phase 5 (US3 Transport)
Developer D: Phase 6 (US4 Inventory) → Phase 7 (US5 Sales)

After all above complete:
Developer A: Phase 11 (Offline Engine)
Developer B: Phase 8 (US6 Community)
Developer C: Phase 10 (US8 Admin)
Developer D: Phase 14 (Testing)

Everyone: Phase 16 (Hardening)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (Auth + Dashboard)
4. **STOP and VALIDATE**: Login, auto-login, logout all work
5. Deploy internal build via EAS for testing

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Auth) → Internal test build (MVP!)
3. US2 (Prices) → Core value delivered
4. US3-5 (Transport, Inventory, Sales) → Full feature parity
5. US6-8 (Community, Notifications, Admin) → Complete platform
6. Offline + Biometric + Observability → Production hardening
7. Testing + CI/CD + Release → Store submission

### Task Count Summary

| Phase | Tasks | Epic Mapping |
|-------|-------|-------------|
| Phase 1: Setup | 17 | Epic 1: Project Setup & Tooling |
| Phase 2: Foundational | 22 | Epic 2: Core Architecture & State Management |
| Phase 3: US1 Auth | 9 | Epic 3: Authentication & Secure Session |
| Phase 4: US2 Prices | 12 | Epic 5: Prices & Forecast Module |
| Phase 5: US3 Transport | 4 | Epic 6: Transport Calculator Module |
| Phase 6: US4 Inventory | 4 | Epic 8: Inventory & Sales Module |
| Phase 7: US5 Sales | 4 | Epic 8: Inventory & Sales Module |
| Phase 8: US6 Community | 5 | Epic 7: Community Module |
| Phase 9: US7 Notifications | 13 | Epic 4: Push Notification Infrastructure |
| Phase 10: US8 Admin | 6 | Epic 8 (Admin subset) |
| Phase 11: Offline | 9 | Epic 9+10: Offline Engine & Conflict Resolution |
| Phase 12: Biometric | 5 | Epic 11: Biometric Session Restore |
| Phase 13: Observability | 5 | Epic 12: Observability & Monitoring |
| Phase 14: Testing | 11 | Epic 14: Testing & QA |
| Phase 15: CI/CD | 4 | Epic 15: CI/CD & Release Pipeline |
| Phase 16: Hardening | 10 | Epic 13+16: Performance + Production |
| **TOTAL** | **140** | |

---

## Notes

- [P] tasks = different files, no dependencies — safe for parallel execution
- [Story] label maps task to specific user story for traceability
- Backend tasks (T078-T085) can be assigned to a backend developer independently
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
