# AgriProfit — Codebase Guide for Code Review

> Use this document to understand what the project does, how it is structured, and how to trace any element you see in the demo back to the source code that produces it.

---

## Table of Contents

1. [What is AgriProfit?](#1-what-is-agriprofit)
2. [Tech Stack at a Glance](#2-tech-stack-at-a-glance)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Repository Layout](#4-repository-layout)
5. [Backend — Deep Dive](#5-backend--deep-dive)
6. [Frontend — Deep Dive](#6-frontend--deep-dive)
7. [Mobile App](#7-mobile-app)
8. [Data Flow — End to End](#8-data-flow--end-to-end)
9. [Authentication Flow](#9-authentication-flow)
10. [Transport Logistics Engine](#10-transport-logistics-engine)
11. [How to Trace a UI Element to Its Code](#11-how-to-trace-a-ui-element-to-its-code)
12. [Key Configuration Files](#12-key-configuration-files)
13. [Testing](#13-testing)

---

## 1. What is AgriProfit?

AgriProfit is an agricultural market intelligence platform built for Indian farmers (initially focused on Kerala). It helps farmers:

- **Track real-time commodity prices** across 100+ mandis (wholesale markets) in India.
- **Forecast future prices** using ML-based models.
- **Decide where to sell** produce by comparing transport costs, spoilage risk, and net profit at different mandis.
- **Manage inventory and sales** to track what they have and what they have earned.
- **Connect with the community** — share tips, ask questions, discuss market conditions.
- **Receive notifications** — price alerts, market announcements, system messages.

---

## 2. Tech Stack at a Glance

| Layer | Technology | Purpose |
|---|---|---|
| **Backend API** | Python · FastAPI | REST API server |
| **ORM** | SQLAlchemy 2 (async-mapped style) | Database access layer |
| **Database** | PostgreSQL | Primary data store |
| **Migrations** | Alembic | Schema versioning |
| **Config** | pydantic-settings | Type-safe env config |
| **Scheduling** | APScheduler | Background price sync every 6 h |
| **External Data** | data.gov.in API | Source of live price records |
| **Auth** | OTP via SMS → JWT | Passwordless login |
| **Rate Limiting** | SlowAPI | Protects all endpoints |
| **Frontend** | Next.js 15 (App Router) · TypeScript | Web app |
| **UI Library** | shadcn/ui + Tailwind CSS | Component library |
| **State / Cache** | TanStack Query (React Query) | Server-state caching |
| **Global Auth State** | Zustand | Client-side auth store |
| **HTTP Client** | Axios | API calls from browser |
| **Charts** | Recharts | Price charts, pie charts |
| **Mobile** | React Native (Expo-style) | Android/iOS app (in progress) |
| **Tests (Backend)** | pytest | Unit + integration |
| **Tests (Frontend)** | Vitest + Testing Library | Component + service tests |

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser / Mobile                      │
│                                                              │
│  Next.js Frontend (port 3000)   React Native Mobile App      │
│  ┌──────────────────────────┐                               │
│  │  Pages (App Router)      │                               │
│  │  Components              │  ─────────────────────────    │
│  │  Services (Axios calls)  │       HTTP / REST JSON         │
│  │  Zustand auth store      │                               │
│  │  React Query cache       │                               │
│  └──────────────────────────┘                               │
└─────────────────────────────────────────────────────────────┘
                             │
                    HTTPS REST API
                    /api/v1/...
                             │
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (port 8000)                     │
│                                                              │
│  main.py ─── registers all routers                          │
│                                                              │
│  Routers ──→ Services ──→ SQLAlchemy Models ──→ PostgreSQL  │
│                                                              │
│  Middleware: CORS · Rate limit · Request logging             │
│  Background: APScheduler ──→ data.gov.in API sync           │
└─────────────────────────────────────────────────────────────┘
                             │
                    PostgreSQL database
```

---

## 4. Repository Layout

```
repo-root/
│
├── backend/                    ← Python FastAPI server
│   ├── app/                    ← All application code
│   │   ├── main.py             ← App entry point, registers everything
│   │   ├── core/               ← Config, logging, rate-limiting, middleware
│   │   ├── database/           ← SQLAlchemy engine + session + base
│   │   ├── models/             ← Database table definitions
│   │   ├── auth/               ← OTP login, JWT tokens
│   │   ├── users/              ← User profiles
│   │   ├── commodities/        ← Commodity catalog
│   │   ├── mandi/              ← Mandi (market) directory
│   │   ├── prices/             ← Historical price data
│   │   ├── forecasts/          ← ML price forecasts
│   │   ├── analytics/          ← Dashboard stats, trends
│   │   ├── transport/          ← Transport cost + logistics engine
│   │   ├── inventory/          ← Farmer's stock management
│   │   ├── sales/              ← Sales records
│   │   ├── community/          ← Posts and discussions
│   │   ├── notifications/      ← Alerts and messages
│   │   ├── admin/              ← Admin audit log
│   │   ├── uploads/            ← Image upload handling
│   │   └── integrations/       ← data.gov.in sync, scheduler
│   ├── alembic/                ← Database migration files
│   ├── tests/                  ← pytest test suite
│   └── scripts/                ← CLI utilities (sync, DB management)
│
├── frontend/                   ← Next.js web app
│   └── src/
│       ├── app/                ← Pages (one folder = one route)
│       ├── components/         ← Reusable UI components
│       ├── services/           ← API call functions (one file per domain)
│       ├── store/              ← Zustand global state
│       ├── hooks/              ← Custom React hooks
│       ├── lib/                ← Axios client, utilities
│       ├── types/              ← TypeScript type definitions
│       └── utils/              ← Performance monitor, helpers
│
├── mobile/                     ← React Native app (in progress)
├── docs/                       ← Planning documents
├── specs/                      ← Feature specifications
├── data/                       ← Reference data files
└── agmarknet_daily_10yr.parquet ← 25M row historical price dataset
```

---

## 5. Backend — Deep Dive

### 5.1 Entry Point: `backend/app/main.py`

This is the **only file that wires everything together**. It:
- Creates the FastAPI application instance.
- Registers all 14 routers under the prefix `/api/v1`.
- Attaches middleware (CORS, rate limiting, request logging, security monitoring, error logging).
- Starts the APScheduler background job that syncs prices from data.gov.in every 6 hours.
- Exposes `/health` and `/sync/status` endpoints.
- Serves uploaded images from `/uploads/images`.

### 5.2 Core Layer: `backend/app/core/`

| File | What it does |
|---|---|
| `config.py` | All environment settings via pydantic-settings. Reads from `backend/.env`. Settings like `DATABASE_URL`, `SECRET_KEY`, `data_gov_api_key`, `diesel_price_per_liter` live here. |
| `logging_config.py` | Structured JSON logging setup. `get_logger(name)` used across every module. |
| `rate_limit.py` | SlowAPI rate limiter. Critical endpoints (OTP) are capped at 1 per 60 s. General API at 100 per minute. |
| `middleware.py` | Three middlewares: **RequestLoggingMiddleware** (logs every request+timing), **SecurityMonitoringMiddleware** (tracks auth failures), **ErrorLoggingMiddleware** (catches unhandled exceptions). |
| `ip_protection.py` | Blocks IPs that repeatedly fail authentication. |

### 5.3 Database Layer: `backend/app/database/`

| File | What it does |
|---|---|
| `session.py` | Creates the SQLAlchemy `engine` and `SessionLocal`. The `get_db()` dependency is injected into every route that needs DB access. |
| `base.py` | Defines `Base` — the declarative base class that all models inherit from. **Important**: import `Base` from here, not from session. |

### 5.4 Models: `backend/app/models/`

Each file defines one database table using SQLAlchemy's `mapped_column` style.

| Model file | Table / Purpose |
|---|---|
| `user.py` | `users` — farmer accounts (phone, name, role, location) |
| `commodity.py` | `commodities` — crop/product catalog |
| `mandi.py` | `mandis` — market locations (name, district, state, coordinates) |
| `price_history.py` | `price_history` — daily min/max/modal prices per commodity per mandi (~25M rows) |
| `price_forecast.py` | `price_forecasts` — ML-generated future price predictions |
| `inventory.py` | `inventory` — farmer's current stock |
| `sale.py` | `sales` — completed sale records |
| `community_post.py` | `community_posts` — discussion posts |
| `notification.py` | `notifications` — user alert records |
| `admin_action.py` | `admin_actions` — audit log of admin operations |
| `otp_request.py` | `otp_requests` — OTP SMS records |
| `login_attempt.py` | `login_attempts` — security tracking |
| `refresh_token.py` | `refresh_tokens` — JWT refresh token store |
| `uploaded_file.py` | `uploaded_files` — metadata for user-uploaded images |
| `road_distance_cache.py` | `road_distance_cache` — caches OSRM routing results |

### 5.5 Feature Modules (each has `routes.py` + `service.py` + `schemas.py`)

Every feature follows the same 3-file pattern:

```
feature/
├── routes.py    ← HTTP endpoints (what URL, method, auth required)
├── service.py   ← Business logic
└── schemas.py   ← Pydantic request/response shapes
```

| Module | URL prefix | What it handles |
|---|---|---|
| `auth/` | `/api/v1/auth` | Request OTP, verify OTP, refresh token, logout |
| `users/` | `/api/v1/users` | Get/update profile, admin user list |
| `commodities/` | `/api/v1/commodities` | List commodities, get details, top by price |
| `mandi/` | `/api/v1/mandis` | List mandis, get by state/district, mandi detail |
| `prices/` | `/api/v1/prices` | Historical price query with filters |
| `forecasts/` | `/api/v1/forecasts` | Upcoming price predictions |
| `analytics/` | `/api/v1/analytics` | Dashboard summary, trends, comparisons |
| `transport/` | `/api/v1/transport` | Transport cost calc, mandi comparison |
| `inventory/` | `/api/v1/inventory` | CRUD for farmer's stock |
| `sales/` | `/api/v1/sales` | Log and query sales |
| `community/` | `/api/v1/community` | Create/list/like posts |
| `notifications/` | `/api/v1/notifications` | Fetch and mark-read notifications |
| `admin/` | `/api/v1/admin` | Admin-only audit log |
| `uploads/` | `/api/v1/uploads` | Upload and serve images |

### 5.6 Integrations: `backend/app/integrations/`

| File | What it does |
|---|---|
| `data_gov_client.py` | HTTP client that fetches price records from data.gov.in API. Handles pagination, retries. |
| `seeder.py` | `DatabaseSeeder` — takes records from the API client and upserts them into `price_history`. |
| `data_sync.py` | `DataSyncService` — orchestrates a full sync run, tracks status (idle/running/error), thread-safe singleton. |
| `scheduler.py` | APScheduler `BackgroundScheduler` that calls `DataSyncService` every N hours (configured via `price_sync_interval_hours`). |

### 5.7 Transport Logistics Engine: `backend/app/transport/`

This is the most sophisticated module. See [Section 10](#10-transport-logistics-engine) for full detail.

---

## 6. Frontend — Deep Dive

### 6.1 Pages (Routes): `frontend/src/app/`

Next.js App Router maps folders to URLs. Every `page.tsx` in a folder is the UI for that route.

| Folder / File | URL | What the user sees |
|---|---|---|
| `page.tsx` | `/` | Landing / redirect page |
| `login/page.tsx` | `/login` | OTP login form |
| `register/page.tsx` | `/register` | New account setup after first OTP verify |
| `dashboard/page.tsx` | `/dashboard` | Main dashboard — stats, top commodities, mandis, activity |
| `dashboard/analyze/page.tsx` | `/dashboard/analyze` | Inventory analysis with forecast |
| `commodities/page.tsx` | `/commodities` | Commodity list with search and sort |
| `commodities/[id]/page.tsx` | `/commodities/:id` | Single commodity detail + price chart |
| `mandis/page.tsx` | `/mandis` | Mandi list with state/district filter |
| `mandis/[id]/page.tsx` | `/mandis/:id` | Single mandi detail + its commodity prices |
| `transport/page.tsx` | `/transport` | Transport calculator — compare mandis by net profit |
| `inventory/page.tsx` | `/inventory` | Farmer's stock (add/edit/delete items) |
| `sales/page.tsx` | `/sales` | Log a sale, view sales history |
| `analytics/page.tsx` | `/analytics` | Market research — trends, heatmaps, comparisons |
| `community/page.tsx` | `/community` | Discussion board — view and create posts |
| `notifications/page.tsx` | `/notifications` | Notification inbox |
| `profile/page.tsx` | `/profile` | Edit user profile, upload avatar |
| `admin/page.tsx` | `/admin` | Admin audit log (admin role only) |
| `api-test/page.tsx` | `/api-test` | Developer diagnostic page for API connectivity |

### 6.2 Components: `frontend/src/components/`

Organized by concern:

#### Layout components (`components/layout/`)

These are the chrome that surrounds every authenticated page.

| File | What it renders |
|---|---|
| `AppLayout.tsx` | Wrapper that puts Sidebar + Navbar + `{children}` together. Most pages use this. |
| `Sidebar.tsx` | Left navigation bar with all menu links. Reads `localStorage` to check if user is admin (shows Admin link). Active link highlighted in green. |
| `Navbar.tsx` | Top bar — page title, user avatar, notification bell. |
| `NotificationBell.tsx` | Bell icon in navbar showing unread count badge. Clicking opens notification dropdown. |
| `Footer.tsx` | Footer shown on public pages. |

#### Dashboard components (`components/dashboard/`)

| File | What it renders |
|---|---|
| `StatCard.tsx` | Individual metric card (e.g. "42 Commodities"). |
| `StatsGrid.tsx` | 4-column grid of `StatCard`s. |
| `CommodityCard.tsx` | Price card for a single commodity in a list. |
| `MarketPricesSection.tsx` | Tabbed section: Current Prices / Historical Trends / Top Movers. |
| `PriceChart.tsx` | Line chart of historical prices (Recharts). |
| `PriceForecastSection.tsx` | Forecast chart + recommendations panel. |
| `tabs/CurrentPricesTab.tsx` | Table of today's mandi prices. |
| `tabs/HistoricalTrendsTab.tsx` | Date-range price trend chart. |
| `tabs/TopMoversTab.tsx` | Commodities with biggest price changes. |
| `forecast/ForecastChart.tsx` | Chart showing predicted future prices. |
| `forecast/ForecastTable.tsx` | Table of forecast rows. |
| `forecast/RecommendationsPanel.tsx` | AI-generated sell/hold recommendation text. |

#### Auth components (`components/auth/`)

| File | What it renders |
|---|---|
| `AuthLayout.tsx` | Centered card layout for login/register pages. |
| `OtpInput.tsx` | 6-box OTP entry field. |
| `ProtectedRoute.tsx` | Wrapper that redirects to `/login` if not authenticated. |

#### UI primitives (`components/ui/`)

These are shadcn/ui components — low-level, unstyled building blocks.

`button.tsx` · `card.tsx` · `input.tsx` · `badge.tsx` · `table.tsx` · `tabs.tsx` · `select.tsx` · `dialog.tsx` · `avatar.tsx` · `skeleton.tsx` · `alert.tsx` · `tooltip.tsx` · `dropdown-menu.tsx` · `popover.tsx` · `form.tsx` · `label.tsx` · `checkbox.tsx` · `textarea.tsx` · `sonner.tsx` (toast notifications) · `empty-state.tsx` · `table-skeleton.tsx`

### 6.3 Services: `frontend/src/services/`

One file per domain. Every function makes an API call and returns typed data. These are called from pages and components (usually via React Query's `queryFn`).

| File | API it calls | Key functions |
|---|---|---|
| `auth.ts` | `/api/v1/auth` | `requestOtp()`, `verifyOtp()`, `logout()` |
| `commodities.ts` | `/api/v1/commodities` | `getAll()`, `getById()`, `getTopCommodities()` |
| `mandis.ts` | `/api/v1/mandis` | `getAll()`, `getById()`, `getStates()`, `getDistricts()` |
| `prices.ts` | `/api/v1/prices` | `getHistory()`, `getLatest()` |
| `forecasts.ts` | `/api/v1/forecasts` | `getForecasts()` |
| `analytics.ts` | `/api/v1/analytics` | `getDashboard()`, `getTrends()`, `getMarketCoverage()` |
| `transport.ts` | `/api/v1/transport` | `compareCosts()`, `getVehicles()`, `getStates()`, `getDistricts()` |
| `inventory.ts` | `/api/v1/inventory` | `getAll()`, `create()`, `update()`, `delete()` |
| `sales.ts` | `/api/v1/sales` | `getAll()`, `create()`, `delete()` |
| `community.ts` | `/api/v1/community` | `getPosts()`, `createPost()`, `likePost()` |
| `notifications.ts` | `/api/v1/notifications` | `getAll()`, `markRead()`, `getRecentActivity()` |
| `admin.ts` | `/api/v1/admin` | `getAuditLog()`, `getUsers()` |

### 6.4 API Client: `frontend/src/lib/api.ts`

Axios instance with:
- Base URL: `NEXT_PUBLIC_API_URL` env var (defaults to `http://127.0.0.1:8000/api/v1`).
- **Request interceptor**: Reads JWT from `localStorage` and attaches `Authorization: Bearer <token>` header to every request.
- **Response interceptor**: On 401 error → clears auth, redirects to `/login`.
- **Performance monitoring**: Records each API call duration via `perfMonitor`.

### 6.5 Auth State: `frontend/src/store/authStore.ts`

Zustand store managing:
- `user` — current user object (name, phone, role).
- `token` — JWT string.
- `isAuthenticated` — boolean.
- `setAuth(user, token)` — called on successful login; persists to `localStorage`.
- `clearAuth()` — called on logout; clears `localStorage`.
- `hydrate()` — called on app mount to restore session from `localStorage`.

### 6.6 Hooks: `frontend/src/hooks/`

| File | What it does |
|---|---|
| `useAuth.ts` | Wraps `useAuthStore`. Provides `user`, `isAuthenticated`, `login()`, `logout()`. |
| `useToast.ts` | Thin wrapper around sonner's `toast()` function. |

### 6.7 Types: `frontend/src/types/index.ts`

Single file defining all shared TypeScript interfaces: `User`, `Commodity`, `CommodityWithPrice`, `Mandi`, `PriceHistory`, `Forecast`, `InventoryItem`, `Sale`, `CommunityPost`, `Notification`, etc.

---

## 7. Mobile App

Located in `mobile/`. A React Native application sharing the same backend API.

```
mobile/
├── App.tsx           ← Root component
├── src/              ← Screens and components
├── package.json      ← React Native dependencies
└── tsconfig.json
```

Uses the same `/api/v1/...` endpoints as the web frontend. Still in active development.

---

## 8. Data Flow — End to End

Here is what happens when a user opens the **Dashboard** page:

```
1. Browser loads /dashboard
2. Next.js renders dashboard/page.tsx
3. Component mounts → useEffect hydrates auth from localStorage
4. React Query fires 3 parallel API calls:
   a. GET /api/v1/analytics/dashboard    → statsData (total commodities, mandis, records, forecasts)
   b. GET /api/v1/commodities?top=5      → top 5 commodities by price
   c. GET /api/v1/notifications/activity → last 5 activity items
5. FastAPI receives each request:
   - Middleware checks JWT, logs request
   - Router calls service function
   - Service queries PostgreSQL via SQLAlchemy
   - Returns JSON response
6. Frontend receives responses → React Query caches them (5 min stale time)
7. Dashboard renders: StatsGrid, MarketPricesSection, Top Commodities list,
   Active Mandis list, Recent Activity, Quick Actions, Data Freshness card
```

**Price Sync background flow:**
```
APScheduler (every 6 hours)
  → DataSyncService.run_sync()
    → data_gov_client.fetch_prices()   (paginates data.gov.in API)
      → DatabaseSeeder.upsert_records() (inserts into price_history table)
        → price_history rows updated
          → next API call returns fresh data
```

---

## 9. Authentication Flow

AgriProfit uses **passwordless OTP login** (no passwords stored):

```
1. User enters phone number on /login
   → frontend: authService.requestOtp(phone)
   → POST /api/v1/auth/request-otp
   → Backend generates 6-digit OTP, stores in otp_requests table, sends SMS

2. User enters OTP
   → frontend: authService.verifyOtp(phone, otp)
   → POST /api/v1/auth/verify-otp
   → Backend validates OTP (5 min expiry, 3 attempt limit)
   → Returns JWT access token + refresh token

3. Frontend receives JWT
   → authStore.setAuth(user, token)  stores in Zustand + localStorage
   → api.ts interceptor attaches token to all future requests

4. On token expiry
   → 401 response → api.ts interceptor clears auth → redirects to /login

5. Admin check
   → Sidebar.tsx reads user.role from localStorage
   → Shows "Admin" nav item only if role === "admin"
```

---

## 10. Transport Logistics Engine

The transport module (`backend/app/transport/`) is the most complex feature. It answers: **"Which mandi should I sell at to make the most profit after transport costs?"**

### Files and responsibilities

| File | What it calculates |
|---|---|
| `economics.py` | `compute_freight()` — diesel-adjusted rate per km, driver bata (per-trip allowance), cleaner bata, halt cost, breakdown reserve, interstate permit fee. Returns `FreightResult`. |
| `spoilage.py` | `SpoilageResult` — exponential decay model: how much produce is lost based on travel time. `HamaliResult` — regional loading/unloading labor costs (North/South/Maharashtra rates). |
| `price_analytics.py` | `PriceAnalytics` — 7-day price volatility (CV%), trend direction, confidence score with penalties for volatile/stale/thin data. |
| `risk_engine.py` | `RiskResult` — composite risk score. `apply_behavioral_corrections()` downgrades the final verdict for far/thin-market/risky destinations. `check_guardrails()` catches scenarios where selling is likely to lose money. |
| `routing.py` | `RoutingService` — gets road distance between two districts: tries DB cache → tries OSRM (live routing) → falls back to haversine × 1.35. Caches successful OSRM results. Uses `ThreadPoolExecutor` for parallel lookups. |
| `service.py` | **Orchestrator** — `compare_mandis()` calls all the above modules, selects optimal vehicle, calculates net profit for each candidate mandi, returns ranked list with audit log. |
| `routes.py` | HTTP endpoints: `POST /transport/compare` (main endpoint), `POST /transport/calculate` (simple estimate), `GET /transport/vehicles`. |
| `schemas.py` | Pydantic shapes for `TransportCompareRequest` and `TransportCompareResponse`. |
| `district_coords.json` | 858 Indian district lat/lon coordinates, loaded at startup for haversine fallback. |

### What the Transport UI shows

The `/transport` page (`frontend/src/app/transport/page.tsx`) has:
1. **Form** — commodity, quantity, source state/district, max distance.
2. **Results table** — each row is one mandi with: distance, price, gross revenue, all costs broken down, net profit, vehicle type, trips needed.
3. **4-tab breakdown** per selected mandi: Costs · Spoilage · Risk · Price Analytics.
4. **Verdict badge** — `GO` / `CAUTION` / `AVOID` badge colour-coded green/amber/red.

Data flows: `transport/page.tsx` → `transportService.compareCosts()` → `POST /api/v1/transport/compare` → `service.compare_mandis()` → all engine modules → JSON response → rendered in table + tabs.

---

## 11. How to Trace a UI Element to Its Code

Use this as your cheat sheet during the demo review:

### "What is that green sidebar on the left?"
→ `frontend/src/components/layout/Sidebar.tsx`
- Menu items array at line 22–32 defines each link (label, icon, href).
- Active item highlighted in green via `isActive` check on `pathname`.

### "What are those 4 stat cards at the top of the dashboard?"
→ `frontend/src/app/dashboard/page.tsx` lines 165–198 build `statsData`.
- Data comes from `analyticsService.getDashboard()` → `GET /api/v1/analytics/dashboard`.
- Rendered in the grid at lines 237–287 using shadcn `Card` component.
- Backend: `backend/app/analytics/routes.py` + `service.py`.

### "What is the 'Market Prices' section below the stats?"
→ `frontend/src/components/dashboard/MarketPricesSection.tsx`
- Contains 3 tabs: Current Prices, Historical Trends, Top Movers.
- Each tab is its own component in `components/dashboard/tabs/`.

### "Where does the price chart data come from?"
→ Chart component: `frontend/src/components/dashboard/PriceChart.tsx` (Recharts `LineChart`).
- Data fetched via: `pricesService.getHistory()` → `GET /api/v1/prices/history`.
- Backend: `backend/app/prices/routes.py` → `service.py` → queries `price_history` table.

### "That Transport page — the comparison table with verdict badges?"
→ `frontend/src/app/transport/page.tsx` (results table with Badge component).
- `verdict` field comes from backend `backend/app/transport/risk_engine.py` → `apply_behavioral_corrections()`.
- Badge colours: green = "GO", amber = "CAUTION", red = "AVOID".

### "The notification bell in the top-right corner?"
→ `frontend/src/components/layout/NotificationBell.tsx`
- Polls `notificationsService.getAll()` → `GET /api/v1/notifications`.
- Shows red badge with unread count.

### "The OTP input boxes on login?"
→ `frontend/src/components/auth/OtpInput.tsx`
- 6 individual input boxes, auto-advances on digit entry.
- Used in `frontend/src/app/login/page.tsx`.

### "The community posts feed?"
→ `frontend/src/app/community/page.tsx`
- Calls `communityService.getPosts()` → `GET /api/v1/community/posts`.
- Backend: `backend/app/community/routes.py` + `service.py`.

### "The inventory table?"
→ `frontend/src/app/inventory/page.tsx`
- CRUD operations via `inventoryService` → `GET/POST/PUT/DELETE /api/v1/inventory`.
- Backend: `backend/app/inventory/routes.py` → `service.py` → `inventory` table.

### "The price forecast chart?"
→ `frontend/src/components/dashboard/forecast/ForecastChart.tsx`
- Data from `forecastsService.getForecasts()` → `GET /api/v1/forecasts`.
- Backend: `backend/app/forecasts/routes.py` → `service.py` → `price_forecasts` table.

### "Any API call — how does auth get attached?"
→ `frontend/src/lib/api.ts` line 22–35 — Axios request interceptor reads JWT from `localStorage` and sets `Authorization: Bearer <token>` header on every request.

### "Where is the backend config (database URL, API keys)?"
→ `backend/app/core/config.py` — pydantic-settings class. Reads from `backend/.env` file.

---

## 12. Key Configuration Files

| File | Purpose |
|---|---|
| `backend/.env` | All backend secrets: `DATABASE_URL`, `SECRET_KEY`, `DATA_GOV_API_KEY`, `DIESEL_PRICE_PER_LITER`, etc. Never committed to git. |
| `backend/alembic.ini` | Alembic migration config — points to the DB URL. |
| `backend/pytest.ini` | Test configuration — test paths, async mode. |
| `frontend/.env.local` | Frontend env: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1`. |
| `frontend/next.config.ts` | Next.js build config. |
| `frontend/tsconfig.json` | TypeScript paths (`@/` maps to `src/`). |
| `frontend/vitest.config.ts` | Vitest test configuration. |
| `docker-compose.prod.yml` | Production Docker Compose for full stack deployment. |

---

## 13. Testing

### Backend Tests (`backend/tests/`)
- Framework: **pytest**
- 86 transport module tests — 100% pass rate.
- Tests cover: unit tests for each transport engine module, integration tests for routes.
- Run: `cd backend && pytest`

### Frontend Tests (`frontend/src/**/__tests__/`)
- Framework: **Vitest + @testing-library/react**
- 38 test files, 598 tests, 100% pass rate.
- Coverage: ~61% statement coverage.
- Located alongside the code they test in `__tests__/` sub-folders.
- Run: `cd frontend && npm test`
- Coverage report: `npm run test:coverage`

### Key test locations
- Page tests: `frontend/src/app/<page>/__tests__/page.test.tsx`
- Component tests: `frontend/src/components/<folder>/__tests__/<Component>.test.tsx`
- Service tests: `frontend/src/services/__tests__/<service>.test.ts`
- UI primitive tests: `frontend/src/components/ui/__tests__/<Component>.test.tsx`
