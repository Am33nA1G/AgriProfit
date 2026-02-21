# API Contract: Existing Endpoint Mapping for Mobile

**Branch**: `001-mobile-app` | **Date**: 2026-02-21

All endpoints are under `{BASE_URL}/api/v1`. No modifications to these endpoints.

## Authentication Flow

| Mobile Action | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| Request OTP | POST | `/auth/request-otp` | Body: `{ phone_number }` |
| Verify OTP | POST | `/auth/verify-otp` | Body: `{ phone_number, otp }` → Returns JWT tokens |
| Complete Profile | POST | `/auth/complete-profile` | Body: `{ name, district, state }` |
| Get Current User | GET | `/auth/me` | Auth required |
| Refresh Token | POST | `/auth/refresh` | Body: `{ refresh_token }` |
| Logout | POST | `/auth/logout` | Auth required, invalidates refresh token |

## Prices & Commodities

| Mobile Screen | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| Commodity List | GET | `/commodities/with-prices` | Paginated, includes latest prices |
| Search Commodities | GET | `/commodities/search/?q=` | Case-insensitive search |
| Commodity Detail | GET | `/commodities/{id}/details` | Includes price history, forecasts |
| Commodity Categories | GET | `/commodities/categories` | For filter UI |
| Price History | GET | `/prices/historical` | Query: `commodity_id`, `days` |
| Current Prices | GET | `/prices/current` | Latest prices all commodities |
| Top Movers | GET | `/prices/top-movers` | Dashboard widget |
| Mandi Prices for Commodity | GET | `/prices/commodity/{id}` | All mandis reporting this commodity |
| Forecasts | GET | `/forecasts/commodity/{id}` | 7-day and 30-day |

## Mandis

| Mobile Screen | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| Mandi List | GET | `/mandis/with-filters` | Paginated, filterable by state/district |
| Mandi Detail | GET | `/mandis/{id}/details` | Includes current prices |
| Mandi Prices | GET | `/mandis/{id}/prices` | All commodity prices at this mandi |
| States List | GET | `/mandis/states` | For location picker |
| Districts List | GET | `/mandis/districts?state=` | For location picker |
| Search Mandis | GET | `/mandis/search/?q=` | By name or market code |

## Transport

| Mobile Screen | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| Calculate Cost | POST | `/transport/calculate` | Body: `{ origin, destination, commodity_id, quantity }` |
| Compare Mandis | POST | `/transport/compare` | Body: `{ origin, commodity_id, mandis[] }` |
| Vehicle Types | GET | `/transport/vehicles` | For form dropdown |
| Supported Districts | GET | `/transport/districts` | For origin picker |

## Inventory

| Mobile Screen | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| List Inventory | GET | `/inventory/` | Auth required, user's items |
| Add Item | POST | `/inventory/` | Body: `{ commodity_id, quantity, unit }` |
| Update Item | PUT | `/inventory/{id}` | Body: `{ quantity, unit }` |
| Delete Item | DELETE | `/inventory/{id}` | Auth required |
| Stock Summary | GET | `/inventory/stock` | Grouped by commodity |
| Sell Analysis | POST | `/inventory/analyze` | Suggests best mandis |

## Sales

| Mobile Screen | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| List Sales | GET | `/sales/` | Auth required, user's sales |
| Record Sale | POST | `/sales/` | Body: `{ commodity_id, quantity, unit, sale_price, buyer_name?, sale_date }` |
| Update Sale | PUT | `/sales/{id}` | Auth required |
| Delete Sale | DELETE | `/sales/{id}` | Auth required |
| Sales Analytics | GET | `/sales/analytics` | Revenue, averages, trends |

## Community

| Mobile Screen | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| List Posts | GET | `/community/posts/` | Paginated, filterable |
| Get Post | GET | `/community/posts/{id}` | Increments view_count |
| Create Post | POST | `/community/posts/` | Auth required |
| Update Post | PUT | `/community/posts/{id}` | Author/admin only |
| Delete Post | DELETE | `/community/posts/{id}` | Author/admin only |
| Search Posts | GET | `/community/posts/search?q=` | Full-text search |
| Get Replies | GET | `/community/posts/{id}/replies` | Paginated |
| Add Reply | POST | `/community/posts/{id}/reply` | Auth required |
| Upvote | POST | `/community/posts/{id}/upvote` | Idempotent |
| Remove Upvote | DELETE | `/community/posts/{id}/upvote` | |
| District Posts | GET | `/community/posts/district/{district}` | For local feed |

## Notifications

| Mobile Screen | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| List Notifications | GET | `/notifications/` | Auth required, paginated |
| Unread Count | GET | `/notifications/unread-count` | For badge |
| Mark Read | PUT | `/notifications/{id}/read` | |
| Mark All Read | PUT | `/notifications/read-all` | |
| Delete Notification | DELETE | `/notifications/{id}` | |
| **Register Push Token** | **POST** | **`/notifications/push-token`** | **NEW endpoint** |
| **Deactivate Push Token** | **DELETE** | **`/notifications/push-token`** | **NEW endpoint** |

## Admin (role-gated)

| Mobile Screen | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| Platform Stats | GET | `/admin/stats` | Admin only |
| User List | GET | `/admin/users` | Admin only |
| Post List | GET | `/admin/posts` | Admin only |
| Ban User | PUT | `/admin/users/{id}/ban` | Admin only |
| Delete Any Post | DELETE | `/admin/posts/{id}` | Admin only |
| Create Notification | POST | `/notifications/` | Admin only, for broadcasts |
| Bulk Notifications | POST | `/notifications/bulk` | Admin only, for district alerts |

## Analytics (Dashboard)

| Mobile Screen | Method | Endpoint | Notes |
|---------------|--------|----------|-------|
| Dashboard Data | GET | `/analytics/dashboard` | Public, cached |
| Market Summary | GET | `/analytics/summary` | Public |
| Top Commodities | GET | `/analytics/top-commodities` | Public |
| Price Trends | GET | `/analytics/price-trends` | Query params |
| Commodity Stats | GET | `/analytics/statistics/{id}` | Avg/min/max/change% |
| Mandi Comparison | GET | `/analytics/comparison/{id}` | Cross-mandi prices |

## Rate Limiting

| Tier | Limit | Applies To |
|------|-------|------------|
| Critical | 5/min | OTP request/verify |
| Write | 30/min | POST/PUT/DELETE operations |
| Read | 100/min | GET operations |
| Analytics | 50/min | Analytics endpoints |

Mobile client must implement exponential backoff when receiving `429 Too Many Requests`.
