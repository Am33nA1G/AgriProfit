# Roadmap: AgriProfit Mobile

## Overview

Six phases deliver complete mobile parity with the AgriProfit web app. Foundation comes first — design tokens, navigation structure, API client, and state libraries must exist before any screen can be built. Authentication gates all screens so it ships next. The three feature screen groups (Dashboard, Commodities, Mandis/Market) build sequentially on authenticated navigation. Cross-cutting UX polish (haptics, toasts, profile) completes the release.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Design tokens, navigation structure, API client, and state libraries
- [ ] **Phase 2: Authentication** - OTP auth flow with SecureStore session management
- [ ] **Phase 3: Dashboard** - First authenticated screen with stat cards and data lists
- [ ] **Phase 4: Commodities** - List browsing, search/filter, and price history charts
- [ ] **Phase 5: Mandis and Market Prices** - Mandi search/filter and market price views
- [ ] **Phase 6: UX Polish** - Toasts, haptics, profile screen, and cross-cutting patterns

## Phase Details

### Phase 1: Foundation
**Goal**: The app has a navigable shell, a single source of design truth, and a configured API+state layer — every subsequent screen can be built without re-litigating infrastructure.
**Depends on**: Nothing (first phase)
**Requirements**: NAV-01, NAV-03, NAV-04, DESIGN-01, DESIGN-02, DESIGN-03, DESIGN-04, DESIGN-05, DESIGN-06, DESIGN-07, DESIGN-08, API-01, API-03, API-04, UX-07
**Success Criteria** (what must be TRUE):
  1. The app launches and shows bottom tabs with 5 tabs (Dashboard, Commodities, Mandis, Analytics, Profile) navigable by tapping
  2. Hardware back button on Android and header back button navigate correctly within stack screens
  3. Tab switches do not trigger unnecessary re-fetches (TanStack Query cache respected across tab focus)
  4. A single `tokens.ts` file defines all colors, typography, spacing, radii, and shadows — no raw hex or pixel values exist outside it
  5. API client sends requests to the correct base URL with `/api/v1` prefix and attaches JWT auth headers; TanStack Query and Zustand are available to all screens
  6. A global error boundary wraps the app root and renders a recovery UI on unhandled JS errors — no blank crash screens
  7. No new state management libraries are introduced; only zustand and TanStack Query are used
**Plans**: TBD

Plans:
- [ ] 01-01: Design tokens (tokens.ts) — extract Tailwind CSS 4 variables from web into single theme file
- [ ] 01-02: Navigation shell — bottom tab navigator with 5 tabs and stack navigators per tab
- [ ] 01-03: API client and state setup — axios client, TanStack Query provider, Zustand store
- [ ] 01-04: Global error boundary — React Native error boundary wrapping app root with recovery UI

### Phase 2: Authentication
**Goal**: Users can authenticate with their phone number via OTP and remain logged in across app restarts until their token expires; all protected screens are correctly guarded.
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10, NAV-02, API-02
**Success Criteria** (what must be TRUE):
  1. User can enter +91 phone number, receive OTP, enter it in 6 individual digit boxes, and reach the authenticated app
  2. OTP auto-submits when the 6th digit is entered; resend countdown timer displays correctly
  3. OTP SMS autofill works on iOS via autoComplete="one-time-code"; Android uses SMS Retriever hash
  4. JWT token is stored in expo-secure-store; user remains logged in across app restarts
  5. Unauthenticated users tapping any protected tab are redirected to the auth screen; 401 API response clears token and redirects; logout clears token
**Plans**: TBD

Plans:
- [ ] 02-01: Phone entry screen — TextInput with +91 prefix, keyboard-aware layout, OTP request
- [ ] 02-02: OTP entry screen — 6-box digit input, auto-submit, resend timer, SMS autofill
- [ ] 02-03: Auth state and navigation guards — SecureStore JWT, session persistence, protected route redirect, logout

### Phase 3: Dashboard
**Goal**: After logging in, users land on a working Dashboard screen that shows current platform stats and data lists, with correct loading/error/refresh handling.
**Depends on**: Phase 2
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. Dashboard shows stat cards (total commodities, total mandis, data freshness indicator) loaded from the API
  2. Dashboard shows top commodities list with current prices and top mandis list
  3. An activity indicator displays while data loads; an error state with retry button displays on API failure
  4. Pull-to-refresh reloads all dashboard data
**Plans**: TBD

Plans:
- [ ] 03-01: Dashboard screen — stat cards, top commodities list, top mandis list
- [ ] 03-02: Loading, error, and pull-to-refresh states on dashboard

### Phase 4: Commodities
**Goal**: Users can browse, search, and filter the full commodity list and navigate to any commodity's detail screen to view price history charts.
**Depends on**: Phase 3
**Requirements**: COMM-01, COMM-02, COMM-03, COMM-04, COMM-05, COMM-06, COMM-07, COMM-08, COMM-09, COMM-10, COMM-11, COMM-12, UX-05
**Success Criteria** (what must be TRUE):
  1. Commodities screen shows a virtualized FlatList of commodity cards with pagination (implementation — onEndReached infinite scroll or load-more button — matches backend API's actual offset/limit model, confirmed before building)
  2. Search input debounces and filters the list; category filters render as a horizontally scrollable chip row
  3. Pull-to-refresh resets and reloads the list; loading state shows activity indicator; error state shows retry button
  4. Tapping a commodity navigates to its detail screen showing name, category, and current min/max/modal prices
  5. Price history line chart (react-native-gifted-charts) renders with 7/30/90-day duration selector, correct ₹ axis labels, and handles loading/error states
**Plans**: TBD

Plans:
- [ ] 04-01: Commodities list — FlatList, search, horizontal category chips, pagination (verify API model first), pull-to-refresh
- [ ] 04-02: Commodity detail — price info display, gifted-charts line chart, duration selector

### Phase 5: Mandis and Market Prices
**Goal**: Users can browse and filter mandis by name/state/district, and view current and historical market price data in a tabbed interface with charts.
**Depends on**: Phase 4
**Requirements**: MANDI-01, MANDI-02, MANDI-03, MANDI-04, MANDI-05, MARKET-01, MARKET-02, MARKET-03, MARKET-04, MARKET-05
**Success Criteria** (what must be TRUE):
  1. Mandis screen shows a virtualized FlatList searchable by name and filterable by state and district
  2. Pull-to-refresh reloads the mandi list; loading and error states with retry are present
  3. Market prices screen has a tab UI with Current Prices tab (price list with commodity, mandi, min/max/modal) and Historical Trends tab (line chart with duration selector)
  4. Both Market Prices tabs handle loading and error states with retry
**Plans**: TBD

Plans:
- [ ] 05-01: Mandis screen — FlatList, name search, state/district filter, pull-to-refresh, loading/error states
- [ ] 05-02: Market prices screen — tab UI, current prices list, historical trends chart (gifted-charts)

### Phase 6: UX Polish
**Goal**: The app feels native and complete: toast notifications provide feedback on auth events, haptic feedback acknowledges key interactions, and users can view their profile and log out.
**Depends on**: Phase 5
**Requirements**: UX-03, UX-04, UX-06
**Success Criteria** (what must be TRUE):
  1. Toast notification appears on OTP request success (code sent), OTP error, and login success
  2. Haptic feedback fires on commodity tap, OTP verify success, and pull-to-refresh complete
  3. Profile screen shows user phone number and a working logout option that clears the session
**Plans**: TBD

Plans:
- [ ] 06-01: Toasts — react-native-toast-message integration on OTP sent, login success, OTP error
- [ ] 06-02: Haptics and profile screen — expo-haptics on key interactions, Profile tab screen with phone number and logout

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/4 | Not started | - |
| 2. Authentication | 0/3 | Not started | - |
| 3. Dashboard | 0/2 | Not started | - |
| 4. Commodities | 0/2 | Not started | - |
| 5. Mandis and Market Prices | 0/2 | Not started | - |
| 6. UX Polish | 0/2 | Not started | - |
