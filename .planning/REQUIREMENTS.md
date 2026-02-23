# Requirements: AgriProfit Mobile

**Defined:** 2026-02-23
**Core Value:** Farmers and traders get the same accurate, real-time market price data on mobile that they get on web — with the same design quality and feature set.

---

## v1 Requirements

Requirements for mobile parity release. Every web feature available to non-admin users must work on mobile.

### Navigation

- [ ] **NAV-01**: App displays bottom tab navigation with 5 tabs: Dashboard, Commodities, Mandis, Analytics, Profile
- [ ] **NAV-02**: Unauthenticated users are redirected to auth screen on any protected tab
- [ ] **NAV-03**: Hardware back button (Android) and header back button navigate correctly within stack
- [ ] **NAV-04**: Navigation state persists correctly across tab switches (no data re-fetches on tab re-focus unless stale)

### Authentication

- [ ] **AUTH-01**: User can enter phone number (+91 prefix) and request OTP
- [ ] **AUTH-02**: User sees 6-box digit OTP input after requesting code
- [ ] **AUTH-03**: OTP auto-submits when the 6th digit is entered
- [ ] **AUTH-04**: OTP SMS autofill works on iOS (autoComplete="one-time-code") and Android (SMS Retriever hash)
- [ ] **AUTH-05**: JWT token is stored in expo-secure-store (not AsyncStorage or localStorage)
- [ ] **AUTH-06**: User remains logged in across app restarts until token expires
- [ ] **AUTH-07**: User can log out from Profile tab; token cleared from SecureStore
- [ ] **AUTH-08**: Expired or missing token redirects user to auth screen automatically
- [ ] **AUTH-09**: OTP resend countdown timer shows correctly on OTP entry screen
- [ ] **AUTH-10**: Keyboard-aware layout prevents forms being hidden behind soft keyboard on both iOS and Android

### Design System

- [ ] **DESIGN-01**: Single `tokens.ts` file defines all design tokens (colors, typography, spacing, radii, shadows)
- [ ] **DESIGN-02**: Primary color is green-600 (#16a34a) used consistently across all interactive elements
- [ ] **DESIGN-03**: Card surfaces use white background with 1px #e5e7eb border and 12px border radius
- [ ] **DESIGN-04**: Typography scale matches web (headings, body, muted text sizes and weights)
- [ ] **DESIGN-05**: Spacing uses 4px base unit consistently (padding-4 = 16px, gap-6 = 24px)
- [ ] **DESIGN-06**: Shadow/elevation tokens applied consistently to cards (elevation: 4 Android, shadow props iOS)
- [ ] **DESIGN-07**: Status colors match web (green-600 for gains, red-600 for losses, gray-500 for muted)
- [ ] **DESIGN-08**: All components reference tokens, not raw hex/pixel values

### Dashboard

- [ ] **DASH-01**: Dashboard screen shows stat cards (total commodities, total mandis, data freshness indicator)
- [ ] **DASH-02**: Dashboard shows top commodities list with current prices
- [ ] **DASH-03**: Dashboard shows top mandis list
- [ ] **DASH-04**: Dashboard data loads with activity indicator and shows error state with retry on failure
- [ ] **DASH-05**: Pull-to-refresh reloads all dashboard data

### Commodities

- [ ] **COMM-01**: Commodities screen shows virtualized FlatList of commodity cards
- [ ] **COMM-02**: User can search commodities by name with debounced text input
- [ ] **COMM-03**: Category filters display as horizontally scrollable chips (not flex-wrap row)
- [ ] **COMM-04**: Commodity list loads additional pages; pagination style (infinite scroll onEndReached vs load-more button) matches backend API's actual pagination model (offset/limit — verify before implementing)
- [ ] **COMM-05**: Pull-to-refresh resets and reloads the commodity list
- [ ] **COMM-06**: Loading state shows activity indicator; error state shows retry button
- [ ] **COMM-07**: Tapping a commodity navigates to commodity detail screen

### Commodity Detail

- [ ] **COMM-08**: Commodity detail shows commodity name, category, current price min/max/modal
- [ ] **COMM-09**: Price history line chart renders using react-native-gifted-charts
- [ ] **COMM-10**: Chart has duration selector: 7 days / 30 days / 90 days
- [ ] **COMM-11**: Chart x-axis labels, y-axis labels, and ₹ currency symbol render correctly
- [ ] **COMM-12**: Chart loading and error states handled with fallback UI

### Mandis

- [ ] **MANDI-01**: Mandis screen shows virtualized FlatList of mandi cards
- [ ] **MANDI-02**: User can search mandis by name
- [ ] **MANDI-03**: User can filter mandis by state and district
- [ ] **MANDI-04**: Pull-to-refresh reloads mandi list
- [ ] **MANDI-05**: Loading and error states with retry on mandis screen

### Market Prices

- [ ] **MARKET-01**: Market prices screen has tab UI: Current Prices and Historical Trends
- [ ] **MARKET-02**: Current Prices tab shows price list with commodity name, mandi, min/max/modal prices
- [ ] **MARKET-03**: Historical Trends tab shows line chart using react-native-gifted-charts
- [ ] **MARKET-04**: Historical Trends chart has duration selector (7/30/90 days)
- [ ] **MARKET-05**: Both tabs handle loading and error states with retry

### UX Patterns

- [ ] **UX-01**: All data-fetching screens show activity indicator while loading
- [ ] **UX-02**: All data-fetching screens show error UI with retry callback (no window.location.reload)
- [ ] **UX-03**: Toast notification shown on OTP request success (code sent), OTP error, and login success
- [ ] **UX-04**: Haptic feedback on commodity tap, OTP verify success, and pull-to-refresh complete
- [ ] **UX-05**: All lists use FlatList for virtualization (no ScrollView + .map() for dynamic lists)
- [ ] **UX-06**: Profile screen shows user phone number and logout option

### API & Infrastructure

- [ ] **API-01**: API client configured with correct base URL, /api/v1 prefix, and auth interceptor (attaches JWT)
- [ ] **API-02**: 401 response from API clears token and redirects to auth screen
- [ ] **API-03**: TanStack React Query used for all server state (same as web)
- [ ] **API-04**: Zustand used for client state (same as web); no new state libraries introduced (no Redux, Jotai, SWR, or any state management package not already in mobile/package.json)
- [ ] **UX-07**: A global React Native error boundary wraps the app root and catches unhandled JS errors, showing a recovery UI (restart/retry) instead of a blank crash screen

---

## v2 Requirements

Deferred to future release. Post-parity enhancements.

### Polish

- **POLISH-01**: Bottom sheet filter panel for advanced Commodities and Mandis filters (@gorhom/react-native-bottom-sheet)
- **POLISH-02**: Filter count badge on filter trigger button showing active filter count
- **POLISH-03**: Native share for commodity price snapshots (Share.share() API)

### Enhanced Location

- **LOC-01**: Geolocation-based mandi proximity sorting (expo-location with foreground permissions)

### Future Charts

- **CHART-01**: Chart gesture zoom/pan on price history (evaluate victory-native-xl upgrade in v2)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Admin panel on mobile | Web-only feature; explicit exclusion in PROJECT.md |
| Grid/list view toggle | Mobile list-only is sufficient; toggle adds complexity for little value on small screen |
| CSV export | DOM APIs (blob, createElement) unavailable; defer to v2 with expo-file-system + expo-sharing |
| Offline mode / full local caching | Data is time-sensitive market pricing; stale price data is harmful; React Query in-memory cache sufficient |
| New features not in web | Parity project — no scope expansion |
| Backend API changes | Mobile consumes existing endpoints unchanged |
| Dark mode | Web has ThemeProvider; mobile theme deferred to v2 |
| Push notifications for price alerts | New feature, not parity |
| recharts on mobile | DOM-based; use react-native-gifted-charts instead |
| New navigation library / Expo Router rewrite | Keep existing navigation structure; no rewrites |
| New state libraries (Redux, Jotai, SWR, etc.) | Use zustand + TanStack Query only |

---

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAV-01 | Phase 1 | Pending |
| NAV-02 | Phase 2 | Pending |
| NAV-03 | Phase 1 | Pending |
| NAV-04 | Phase 1 | Pending |
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
| AUTH-06 | Phase 2 | Pending |
| AUTH-07 | Phase 2 | Pending |
| AUTH-08 | Phase 2 | Pending |
| AUTH-09 | Phase 2 | Pending |
| AUTH-10 | Phase 2 | Pending |
| DESIGN-01 | Phase 1 | Pending |
| DESIGN-02 | Phase 1 | Pending |
| DESIGN-03 | Phase 1 | Pending |
| DESIGN-04 | Phase 1 | Pending |
| DESIGN-05 | Phase 1 | Pending |
| DESIGN-06 | Phase 1 | Pending |
| DESIGN-07 | Phase 1 | Pending |
| DESIGN-08 | Phase 1 | Pending |
| DASH-01 | Phase 3 | Pending |
| DASH-02 | Phase 3 | Pending |
| DASH-03 | Phase 3 | Pending |
| DASH-04 | Phase 3 | Pending |
| DASH-05 | Phase 3 | Pending |
| COMM-01 | Phase 4 | Pending |
| COMM-02 | Phase 4 | Pending |
| COMM-03 | Phase 4 | Pending |
| COMM-04 | Phase 4 | Pending |
| COMM-05 | Phase 4 | Pending |
| COMM-06 | Phase 4 | Pending |
| COMM-07 | Phase 4 | Pending |
| COMM-08 | Phase 4 | Pending |
| COMM-09 | Phase 4 | Pending |
| COMM-10 | Phase 4 | Pending |
| COMM-11 | Phase 4 | Pending |
| COMM-12 | Phase 4 | Pending |
| MANDI-01 | Phase 5 | Pending |
| MANDI-02 | Phase 5 | Pending |
| MANDI-03 | Phase 5 | Pending |
| MANDI-04 | Phase 5 | Pending |
| MANDI-05 | Phase 5 | Pending |
| MARKET-01 | Phase 5 | Pending |
| MARKET-02 | Phase 5 | Pending |
| MARKET-03 | Phase 5 | Pending |
| MARKET-04 | Phase 5 | Pending |
| MARKET-05 | Phase 5 | Pending |
| UX-01 | Phase 3 | Pending |
| UX-02 | Phase 3 | Pending |
| UX-03 | Phase 6 | Pending |
| UX-04 | Phase 6 | Pending |
| UX-05 | Phase 4 | Pending |
| UX-06 | Phase 6 | Pending |
| API-01 | Phase 1 | Pending |
| API-02 | Phase 2 | Pending |
| API-03 | Phase 1 | Pending |
| API-04 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 59 total (NAV: 4, AUTH: 10, DESIGN: 8, DASH: 5, COMM: 12, MANDI: 5, MARKET: 5, UX: 6, API: 4)
- Mapped to phases: 59/59
- Unmapped: 0

---
*Requirements defined: 2026-02-23*
*Last updated: 2026-02-23 — traceability finalized during roadmap creation*
