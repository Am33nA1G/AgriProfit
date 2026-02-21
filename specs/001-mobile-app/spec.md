# Feature Specification: AgriProfit Mobile Application

**Feature Branch**: `001-mobile-app`
**Created**: 2026-02-21
**Status**: Draft
**Input**: User description: "Production-grade React Native mobile app for AgriProfit — connecting to existing FastAPI backend, supporting all V1 features including price tracking, forecasts, transport, inventory, sales, community, and notifications."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phone-Based Login (Priority: P1)

A farmer opens the AgriProfit mobile app for the first time, enters their phone number, receives a one-time password via SMS, enters it, and gains access to their personalized dashboard. On subsequent opens, they are automatically logged in until their session expires or they log out.

**Why this priority**: Authentication is the gateway to all other features. Without login, no feature is accessible. This must work flawlessly on low-end devices and slow networks common in rural India.

**Independent Test**: Can be fully tested by entering a phone number, receiving OTP, and verifying the app shows the dashboard. Delivers immediate value by granting access to all price data.

**Acceptance Scenarios**:

1. **Given** the farmer has not logged in, **When** they open the app, **Then** they see a login screen requesting their phone number.
2. **Given** the farmer enters a valid 10-digit Indian phone number, **When** they tap "Send OTP", **Then** an OTP is sent to their phone and the app navigates to the OTP entry screen.
3. **Given** the farmer has received the OTP, **When** they enter the correct 6-digit code within 5 minutes, **Then** they are authenticated and taken to the dashboard.
4. **Given** the farmer enters an incorrect OTP, **When** they submit it, **Then** they see an error message and can retry (up to 3 attempts).
5. **Given** the farmer's session token has expired, **When** they open the app, **Then** the app silently refreshes the token without requiring re-login (if refresh token is valid).
6. **Given** the farmer's refresh token has also expired, **When** they open the app and biometrics are enrolled, **Then** they are prompted for fingerprint/face unlock to restore their session without OTP.
7. **Given** biometrics are unavailable or not enrolled, **When** the farmer's session needs re-authentication, **Then** they are prompted for their PIN as a fallback.
8. **Given** the farmer taps "Logout", **When** confirmed, **Then** their session is cleared and they return to the login screen.

---

### User Story 2 - Browse Commodity Prices (Priority: P1)

A farmer opens the app and sees a list of agricultural commodities with their latest prices. They tap on a commodity (e.g., Wheat) and see a detailed price history chart, current prices across nearby mandis, and 7-day/30-day forecasts — helping them decide when and where to sell.

**Why this priority**: Price information is the core value proposition. Farmers need instant access to prices to make time-sensitive selling decisions.

**Independent Test**: Can be tested by browsing commodities, tapping one, and verifying the price chart, mandi comparison, and forecast data are displayed correctly.

**Acceptance Scenarios**:

1. **Given** the farmer is logged in, **When** they navigate to the Prices section, **Then** they see a searchable list of all available commodities with their latest modal price.
2. **Given** the farmer taps a commodity, **When** the detail screen loads, **Then** they see a price history chart (default 30-day view), the latest price across mandis, and forecast data.
3. **Given** the farmer is viewing a commodity, **When** they toggle between 7-day and 30-day forecast views, **Then** the chart and forecast data update accordingly.
4. **Given** the farmer wants to compare prices, **When** they view the mandi comparison section, **Then** they see prices from multiple mandis sorted by price (highest first).
5. **Given** the farmer is on a slow network, **When** price data is loading, **Then** they see a loading indicator and previously cached data (if available) is shown as a placeholder.

---

### User Story 3 - Transport Cost & Profitability Comparison (Priority: P2)

A farmer wants to sell their produce and needs to decide which mandi offers the best net profit after transport costs. They enter their location, select a commodity, and the app calculates transport costs to nearby mandis, showing which mandi yields the highest profit.

**Why this priority**: Transport cost is a major factor in farmer profitability. Showing net profit (price minus transport) turns raw price data into actionable decisions.

**Independent Test**: Can be tested by entering origin location, selecting a commodity, and verifying the app shows multiple mandis ranked by net profitability.

**Acceptance Scenarios**:

1. **Given** the farmer navigates to Transport, **When** they enter their origin location and select a commodity, **Then** the app shows nearby mandis with estimated transport cost and net profit for each.
2. **Given** results are displayed, **When** the farmer views the comparison, **Then** mandis are ranked by net profitability (commodity price minus transport cost).
3. **Given** the farmer taps a mandi in the results, **When** the detail view opens, **Then** they see breakdown: commodity price, transport cost, estimated net profit, and distance.

---

### User Story 4 - Inventory Management (Priority: P2)

A farmer tracks their stored produce by adding inventory entries with commodity type, quantity, and storage date. They can view their full inventory, see the current market value of their holdings, and delete entries when produce is sold.

**Why this priority**: Inventory tracking helps farmers understand what they have and its market value — directly supporting selling decisions.

**Independent Test**: Can be tested by adding an inventory entry, viewing it in the list, checking the calculated market value, and deleting the entry.

**Acceptance Scenarios**:

1. **Given** the farmer navigates to Inventory, **When** they tap "Add Inventory", **Then** a form appears to enter commodity, quantity, and storage date.
2. **Given** valid inventory data is entered, **When** the farmer submits, **Then** the entry appears in their inventory list immediately.
3. **Given** the farmer has inventory entries, **When** they view the inventory screen, **Then** each entry shows the commodity, quantity, storage date, and current estimated market value.
4. **Given** the farmer wants to remove an entry, **When** they swipe or tap delete and confirm, **Then** the entry is removed from the list.

---

### User Story 5 - Sales Tracking (Priority: P2)

A farmer records completed sales with commodity, quantity, price, and date. They can view their sales history and see analytics (total revenue, average price per commodity, sales trends).

**Why this priority**: Sales history helps farmers track income and spot trends in their selling patterns.

**Independent Test**: Can be tested by recording a sale, viewing it in history, and verifying analytics calculations.

**Acceptance Scenarios**:

1. **Given** the farmer navigates to Sales, **When** they tap "Record Sale", **Then** a form appears to enter commodity, quantity, sale price, and date.
2. **Given** valid sale data is entered, **When** the farmer submits, **Then** the sale appears in their history immediately.
3. **Given** the farmer has recorded sales, **When** they view the analytics section, **Then** they see total revenue, average prices, and trend indicators.

---

### User Story 6 - Community Forum (Priority: P3)

A farmer participates in a community discussion board where they can read posts from other farmers, create new posts, reply to existing discussions, and like helpful content.

**Why this priority**: Community engagement builds trust and retention but is not critical for the core price intelligence use case.

**Independent Test**: Can be tested by browsing posts, creating a new post, replying to another post, and liking a post.

**Acceptance Scenarios**:

1. **Given** the farmer navigates to Community, **When** the screen loads, **Then** they see a list of recent posts with title, author, timestamp, and like count.
2. **Given** the farmer taps "New Post", **When** they enter a title and body and submit, **Then** the post appears at the top of the feed.
3. **Given** the farmer views a post, **When** they tap "Reply", **Then** they can type and submit a reply that appears in the thread.
4. **Given** the farmer sees a helpful post, **When** they tap the like button, **Then** the like count increments and their like is recorded.
5. **Given** the farmer authored a post, **When** they tap delete on their own post and confirm, **Then** the post is removed.

---

### User Story 7 - Notifications & Alerts (Priority: P3)

A farmer receives push notifications for price alerts in their district, replies to their forum posts, and admin broadcasts. They can view all notifications in-app and mark them as read.

**Why this priority**: Notifications drive re-engagement and timely action, but the app is functional without them.

**Independent Test**: Can be tested by triggering a district alert, verifying the push notification arrives, opening the notification center, and marking notifications as read.

**Acceptance Scenarios**:

1. **Given** a district-based price alert is triggered, **When** the farmer has notifications enabled, **Then** they receive a push notification on their device.
2. **Given** someone replies to the farmer's forum post, **When** the reply is posted, **Then** the farmer receives a notification.
3. **Given** the farmer opens the Notifications screen, **When** it loads, **Then** they see all notifications sorted by most recent, with unread ones visually distinguished.
4. **Given** the farmer taps a notification, **When** it opens, **Then** it is marked as read and navigates to the relevant content.

---

### User Story 8 - Admin Management (Priority: P3)

An admin user accesses platform management features including broadcasting alerts to all users or specific districts, moderating community posts (delete any post), and viewing platform-wide statistics.

**Why this priority**: Admin features are essential for platform operation but affect only admin users, not the farmer majority.

**Independent Test**: Can be tested by logging in as admin, broadcasting an alert, deleting a community post, and viewing platform statistics.

**Acceptance Scenarios**:

1. **Given** a user with admin role logs in, **When** they access the app, **Then** they see an additional "Admin" section in navigation.
2. **Given** the admin navigates to Admin, **When** they compose and send a broadcast alert, **Then** the alert is delivered to target users as a notification.
3. **Given** the admin views a community post, **When** they tap delete on any post, **Then** the post is removed regardless of authorship.
4. **Given** the admin views platform stats, **When** the screen loads, **Then** they see user counts, post counts, and price data health metrics.

---

### Edge Cases

- What happens when the farmer has no internet connection? The app displays cached data (if available) and shows a clear offline indicator. Actions requiring network (posting, recording sales) queue locally and sync when connectivity returns.
- What happens when the session token expires during active use? The app silently refreshes the token. If refresh fails, redirects to login with a message explaining the session expired.
- What happens when the farmer's OTP expires before entry? The app shows an expiry message and offers a "Resend OTP" option with a cooldown timer.
- What happens when the farmer searches for a commodity that doesn't exist? The app shows "No results found" with a suggestion to check spelling or browse categories.
- What happens when the farmer tries to delete inventory while offline? The delete is queued and a visual indicator shows the entry is "pending deletion" until sync completes.
- What happens when push notification permissions are denied? The app still functions fully, with notifications available only in-app. A non-intrusive prompt periodically reminds the user to enable notifications.
- What happens when the farmer's device storage is full and cached data cannot be saved? The app gracefully degrades to online-only mode without crashing, clearing oldest cache entries first.
- What happens when the backend returns rate-limit errors? The app automatically retries after the appropriate delay and shows a "please wait" indicator to the user.
- What happens when an offline-queued write conflicts with a change made on the web? The mobile change wins (last-write-wins). The user sees a brief notification that a conflict was resolved, with an option to view what was overwritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to authenticate using their phone number and a one-time password (OTP).
- **FR-002**: System MUST securely store authentication credentials on the device so users remain logged in across app restarts.
- **FR-003**: System MUST silently refresh expired session tokens using stored refresh credentials without requiring user re-authentication.
- **FR-004**: System MUST display a searchable, filterable list of all agricultural commodities with their latest prices.
- **FR-005**: System MUST display price history charts for any selected commodity with configurable time ranges (7-day, 30-day).
- **FR-006**: System MUST show price comparisons for a commodity across multiple mandis, sorted by price.
- **FR-007**: System MUST display 7-day and 30-day price forecasts for selected commodities.
- **FR-008**: System MUST calculate transport costs from the farmer's location to nearby mandis and show net profitability per mandi.
- **FR-009**: System MUST allow farmers to add, view, and delete inventory entries (commodity, quantity, storage date).
- **FR-010**: System MUST display the current estimated market value for each inventory entry based on latest prices.
- **FR-011**: System MUST allow farmers to record sales with commodity, quantity, sale price, and date.
- **FR-012**: System MUST display sales analytics including total revenue, average price per commodity, and trend indicators.
- **FR-013**: System MUST allow farmers to browse, create, reply to, like, and delete (own) community posts.
- **FR-014**: System MUST deliver push notifications for district-based price alerts, forum replies, and admin broadcasts.
- **FR-015**: System MUST display an in-app notification center with read/unread status and navigation to relevant content.
- **FR-016**: System MUST provide admin users with the ability to broadcast alerts, delete any post, and view platform statistics.
- **FR-017**: System MUST cache recently viewed data for offline access (commodity prices, user inventory, sales history).
- **FR-018**: System MUST queue write operations (new posts, sales entries, inventory changes) when offline and sync when connectivity is restored. Conflicts are resolved using last-write-wins: the mobile change overwrites the server state, and the user is notified if a conflict was detected during sync.
- **FR-019**: System MUST display a clear offline/online status indicator.
- **FR-020**: System MUST handle backend rate-limit responses with automatic retry and user-facing feedback.
- **FR-021**: System MUST show admin-only navigation and screens exclusively to users with the admin role.
- **FR-022**: System MUST support pull-to-refresh on all list screens to fetch the latest data.
- **FR-023**: System MUST register and update the device push token with the backend on login, app launch, and token refresh so the backend can deliver targeted push notifications.
- **FR-024**: System MUST capture and report application crashes and unhandled errors to a monitoring service for production diagnostics.
- **FR-025**: System MUST collect basic usage analytics (screen views, feature adoption rates, session duration) to inform product decisions, with user privacy respected.
- **FR-026**: System MUST offer biometric authentication (fingerprint or face recognition) for returning users to restore an expired session without requiring OTP re-entry.
- **FR-027**: System MUST provide a PIN-based fallback for session restoration on devices that do not support biometrics or where the user has not enrolled biometrics.

### Key Entities

- **User**: A person using the app. Has a phone number, name, district, role (Farmer or Admin), and authentication credentials. One user may have many inventory entries, sales records, and community posts.
- **Commodity**: An agricultural product (e.g., Wheat, Rice, Onion) with a name, category, and current market price. Has price history across time and mandis.
- **Mandi**: An agricultural market with a name, location (state, district), and geographic coordinates. Reports daily prices for multiple commodities.
- **Price Record**: A price observation for a specific commodity at a specific mandi on a specific date. Contains minimum, maximum, and modal prices.
- **Forecast**: A predicted price for a commodity over a future period (7-day or 30-day), with confidence indicators.
- **Inventory Entry**: A farmer's stored produce record containing commodity, quantity, storage date, and calculated market value.
- **Sale Record**: A completed sale containing commodity, quantity, sale price, date, and optionally buyer information.
- **Community Post**: A user-created discussion entry with title, body, timestamp, author, like count, and replies.
- **Notification**: A message delivered to a user, with type (alert, reply, broadcast), content, read status, timestamp, and navigation target.
- **Transport Estimate**: A calculated cost to move produce from an origin to a destination mandi, including distance and cost breakdown.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Farmers can complete login (phone number entry through dashboard access) in under 60 seconds on a 3G connection.
- **SC-002**: 95% of commodity price lookups return visible results within 3 seconds on a standard mobile connection.
- **SC-003**: The app remains usable (viewing previously loaded data) without any internet connection.
- **SC-004**: Farmers can record a sale or add inventory in under 30 seconds.
- **SC-005**: Push notifications are delivered to 90%+ of opted-in users within 2 minutes of the triggering event.
- **SC-006**: The app launches to a usable state (cached dashboard or login screen) in under 3 seconds on a mid-range device.
- **SC-007**: All queued offline actions sync successfully within 30 seconds of connectivity being restored.
- **SC-008**: Farmers using both web and mobile platforms see consistent data across both within 1 minute of any update.
- **SC-009**: 80% of first-time users can complete the login flow without external assistance.
- **SC-010**: The app supports at least 1,000 concurrent users without degraded performance.
- **SC-011**: The transport profitability comparison displays results for at least 3 nearby mandis within 5 seconds of query submission.
- **SC-012**: The app consumes less than 100MB of device storage for cached data under normal usage.

## Scope Boundaries *(mandatory)*

### In Scope

- All features listed in Functional Requirements (FR-001 through FR-022)
- Android (10+ / API 29+) and iOS (15+) platforms
- Hindi and English language support
- Offline data caching and queued write operations
- Push notifications via device-native notification services
- Secure on-device credential storage
- Integration with the existing backend (no backend changes required)

### Out of Scope

- Backend API modifications or new endpoints (except the single push token registration endpoint defined in FR-023)
- Web application changes
- Payment processing or in-app purchases
- Voice input or accessibility beyond standard platform guidelines
- Crop disease detection or image recognition features
- GPS-based automatic mandi detection (user manually selects location)
- Real-time chat or messaging between users
- Multi-language support beyond Hindi and English in V1
- Tablet-optimized layouts (phone-first, tablets use phone layout)

## Dependencies *(mandatory)*

- **Existing Backend API**: All mobile features depend on the existing FastAPI backend under `/api/v1`. One minimal backend addition is required: a new endpoint to register and update device push tokens (see FR-023).
- **Push Notification Service**: Requires Expo Push Notifications as the delivery API, which uses Firebase Cloud Messaging (FCM) on Android and Apple Push Notification service (APNs) on iOS under the hood. The backend stores device push tokens via a new registration endpoint and sends notifications through the Expo Push API.
- **App Store Accounts**: Apple Developer Program ($99/year) and Google Play Developer account ($25 one-time) are required for distribution.
- **OTP Delivery Service**: The existing backend OTP delivery mechanism must support SMS delivery to Indian phone numbers.
- **Device Permissions**: Notifications and network access permissions are required.

## Assumptions

- The existing backend API is stable and will not change its contract during mobile development.
- All 113+ existing REST endpoints are sufficient to support the mobile feature set, with one addition: a push token registration endpoint.
- The backend accepts requests from native mobile clients without CORS issues (native apps do not send CORS headers).
- OTP delivery to Indian mobile numbers is handled by the backend and works reliably.
- Farmers primarily use Android devices (80%+) with mid-range specifications (2GB+ RAM). Minimum supported versions: Android 10 (API 29), iOS 15.
- Internet connectivity in rural India is intermittent; 3G/4G speeds range from 1-10 Mbps.
- The backend's rate limiting (4 tiers: critical 5/min, write 30/min, read 100/min, analytics 50/min) will not change.
- Price data may lag by 1-2 days; the app uses the latest available date from the backend as the reference date.
- The web app's design system (color palette, typography scale, spacing) serves as the baseline for mobile UI consistency.
- Hindi translations will be provided separately; the app architecture supports runtime language switching.
- Admin users are a small percentage (<1%) of the total user base.
- The existing JWT token expiry (24 hours) and refresh mechanism remain unchanged.

## Risks & Mitigations

| Risk                                                         | Likelihood | Impact | Mitigation                                                                                              |
|--------------------------------------------------------------|-----------|--------|--------------------------------------------------------------------------------------------------------|
| Poor rural network connectivity causes frequent failures     | High      | High   | Aggressive caching, offline queue, optimistic UI updates, compressed payloads                           |
| Low-end devices struggle with chart rendering                | Medium    | Medium | Lazy loading, simplified chart views for low-memory devices, virtualized lists                          |
| Backend rate limits block mobile users during peak usage     | Medium    | High   | Client-side request debouncing, intelligent cache-first strategy, exponential backoff                   |
| Push notification delivery failures in rural areas           | High      | Medium | In-app notification center as fallback, local notification scheduling for cached alerts                 |
| App store rejection due to policy violations                 | Low       | High   | Pre-submission compliance review, follow platform guidelines strictly                                   |
| Data inconsistency between web and mobile                    | Medium    | Medium | Shared backend ensures single source of truth; cache invalidation on app foreground                     |
| OTP SMS delivery delays in rural areas                       | High      | High   | Allow 5-minute OTP validity, clear retry UI, future support for WhatsApp OTP delivery                   |

## Clarifications

### Session 2026-02-21

- Q: How should device push token registration be handled given the "no backend changes" constraint? → A: Allow minimal backend addition — one new endpoint to register/update device push tokens (FR-023 added). Scope boundary updated to reflect this exception.
- Q: What should happen when an offline-queued mobile write conflicts with a change already made on the web? → A: Last-write-wins — mobile sync overwrites server state; user is notified if a conflict was detected.
- Q: Should the app include crash reporting and usage analytics? → A: Yes — both crash reporting (error tracking) and basic usage analytics (screen views, feature adoption, session duration).
- Q: What are the minimum supported platform versions? → A: Android 10 (API 29) and iOS 15.
- Q: Should the app support biometric authentication for returning users? → A: Yes — biometric unlock (fingerprint/face) to restore session, with PIN fallback if biometrics unavailable.
