# AgriProfit - Claude Code Context

## Project Overview

AgriProfit is a production-grade SaaS platform helping Indian farmers make data-driven decisions about commodity sales. It provides real-time price tracking across 500+ mandis (agricultural markets), price forecasting, transport cost optimization, inventory management, and a community forum.

**Status:** V1.2 feature-complete. Auth UI redesigned, community forum enhanced with alert system, data sync active, price gap backfill scripts in place. Next step: production deployment.

## Tech Stack

### Backend
- **Python 3.12** / **FastAPI 0.128** / **SQLAlchemy 2.0** (mapped_column style)
- **PostgreSQL 15+** via psycopg3 driver (`postgresql+psycopg://`)
- **Alembic** for migrations (15 versions), **APScheduler 3.10.4** for background jobs
- **JWT + OTP** phone-based auth (python-jose, HS256, 24hr expiry)
- **Redis** for rate limiting in production (in-memory for dev)
- **slowapi** for rate limiting (4 tiers: critical/write/read/analytics)
- **httpx** for HTTP client (data.gov.in API calls)
- **pydantic-settings 2.12** for config, loads from `backend/.env`
- **python-dotenv** for environment loading
- **Faker** + **pytest** + **pytest-cov** + **pytest-asyncio** for testing
- **python-json-logger** for structured logging

### Frontend
- **Next.js 15.5.9** (App Router) / **React 19** / **TypeScript 5**
- **Tailwind CSS 4** + **Radix UI** / **shadcn/ui** components
- **Recharts 3.7** for charts, **Zustand 5** for global state, **React Query 5** for server state
- **Vitest 1.6** (NOT Jest) for testing with **jsdom** environment
- **Axios 1.13** for HTTP, **Zod 4** for schema validation
- **react-hook-form 7** + **@hookform/resolvers** for forms
- **next-intl 4.8** for internationalization
- **next-themes 0.4.6** for dark mode support
- **sonner 2.0** for toast notifications
- **lucide-react 0.563** for icons
- **class-variance-authority** + **clsx** + **tailwind-merge** for className utilities
- **tw-animate-css** for animations
- **MSW 2.0** for API mocking in tests
- **@testing-library/react 16** + **@testing-library/user-event 14** for component testing

### Database
- PostgreSQL with **25M+ rows** in `price_history`, **16 models**, **456 commodities**, **5,654 mandis**

### Infrastructure
- **Docker Compose** (production) with 5 services: backend, frontend, postgres, redis, nginx
- **Nginx** reverse proxy with SSL support on :80/:443
- **GitHub Actions** CI with AI-powered code review (Groq API)

## Directory Structure

```
backend/
  app/
    main.py                      # FastAPI entry point
    core/
      config.py                  # Settings (pydantic-settings, env-based)
      rate_limit.py              # slowapi rate limiting (4 tiers)
    middleware/
      logging.py                 # Request logging, slow request warnings (>1s)
      security.py                # Auth failure tracking, admin endpoint logging
      error.py                   # Unhandled exception logging
    database/session.py          # Engine, SessionLocal
    models/                      # 16 SQLAlchemy models (UUID PKs everywhere)
    auth/                        # JWT + OTP auth (routes.py, security.py)
    users/routes.py
    commodities/                 # routes.py, service.py
    mandi/                       # routes.py, service.py
    prices/                      # routes.py, service.py
    forecasts/routes.py
    transport/                   # routes.py, service.py
    community/                   # routes.py, service.py, schemas.py, alert_service.py, district_neighbors.py
    notifications/routes.py
    admin/routes.py
    analytics/                   # routes.py, service.py, mv_helpers.py, refresh_views.py
    inventory/                   # routes.py, service.py
    sales/routes.py
    uploads/routes.py
    integrations/                # data_gov_client.py, seeder.py, data_sync.py, scheduler.py
  scripts/                       # 30+ utility scripts (see Scripts section)
  alembic/                       # Database migrations (15 versions)
  tests/                         # pytest tests with SQLite in-memory

frontend/
  src/
    app/                         # Next.js pages (18 routes)
      dashboard/                 # With /analyze subroute
      commodities/[id]/          # Dynamic commodity pages
      mandis/[id]/               # Dynamic mandi pages
      admin/                     # Admin panel
      analytics/                 # Analytics dashboard with price charts
      community/                 # Community forum
      inventory/                 # Inventory management
      sales/                     # Sales tracking
      transport/                 # Transport/logistics
      profile/                   # User profile
      notifications/             # Notifications center
      login/                     # Login page
      register/                  # Registration page
      api-test/                  # API testing utility
    components/
      layout/                    # AppLayout, Sidebar, Navbar
      ui/                        # shadcn/ui components (20+)
      dashboard/                 # Dashboard-specific components + tabs/
      auth/                      # AuthLayout, OtpInput, ProtectedRoute
    services/                    # 12 API service modules (auth, prices, commodities, etc.)
    lib/api.ts                   # Axios client with auth interceptor
```

## Critical Performance Rules

The `price_history` table has **~25M rows**. Violating these rules causes 60+ second timeouts:

1. **ALWAYS add date filters** when querying `price_history`
2. **Use `MAX(price_date)` as reference date**, not `date.today()` - data may lag by days
3. **Use `ORDER BY + LIMIT 1` instead of `MIN()`/`MAX()`** on large tables - indexes are DESC
4. **Avoid window functions** (LAG, FIRST_VALUE) without date bounds
5. Use **DISTINCT ON** + **LEFT JOIN LATERAL** for latest-per-group queries
6. Use **pg_class reltuples** for approximate counts, not `COUNT(*)`
7. Price normalization: values < 200 are multiplied by 100 (kg to quintal conversion)

## Key Conventions

### Backend
- ORM: SQLAlchemy 2.0 `Mapped` / `mapped_column` style (NOT legacy `Column`)
- All PKs are UUID (`PG_UUID(as_uuid=True)`)
- snake_case for files/functions/variables, PascalCase for classes
- Type hints required on all function signatures
- DB driver: `postgresql+psycopg://` (psycopg 3, NOT psycopg2)
- API prefix: `/api/v1`
- Rate limiting: slowapi with 4 tiers (critical: 5/min, write: 30/min, read: 100/min, analytics: 50/min)
- Logging: python-json-logger, request IDs via UUID in middleware
- Security: Auth failure tracking per IP, admin endpoint monitoring

### Frontend
- Testing: **Vitest** (NOT Jest) with jsdom environment
- API base URL: `NEXT_PUBLIC_API_URL` env var (must include `/api/v1`)
- CORS origins: `http://localhost:3000` and `http://127.0.0.1:3000`
- Functional components only (no class components)
- State: Zustand for global, React Query for server state
- Forms: react-hook-form + zod validation
- Charts: Recharts with `connectNulls` on Line components for sparse data
- Dynamic imports for Recharts (SSR disabled): `dynamic(() => import("recharts").then(mod => mod.X), { ssr: false })`
- Toast notifications: sonner (`toast.success()`, `toast.error()`)
- Icons: lucide-react (never use Proxy mock in tests)
- Security headers: HSTS, X-XSS-Protection, X-Frame-Options: SAMEORIGIN

### Vitest Gotchas
- `useRouter` mocks MUST return stable object references (use `vi.hoisted()`)
- lucide-react: Never use Proxy mock; use explicit named exports
- Variables referenced in `vi.mock` factories need `vi.hoisted()`
- Memory limit: 4096MB (`--max-old-space-size=4096` in vitest config)

### Test Infrastructure
- **Backend**: SQLite in-memory for tests (`tests/conftest.py`), pytest markers for unit/integration/slow
- **Frontend**: vitest + @testing-library/react + msw for API mocking
- **conftest.py**: Must keep SQLite table schemas in sync with SQLAlchemy models (commodities, mandis, users tables have extra columns vs original schema)

## Common Commands

```bash
# Backend
cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload  # Dev server (port 8000)
cd backend && alembic upgrade head                                       # Run migrations
cd backend && DATABASE_URL=postgresql+psycopg://user:pass@localhost/agriprofit pytest --cov=app  # Tests
cd backend && python scripts/sync_now.py                                 # Manual data sync

# Frontend
cd frontend && npm run dev        # Dev server (port 3000)
cd frontend && npm test           # Run tests (vitest)
cd frontend && npx vitest run --coverage  # Tests with coverage

# Database
cd backend && alembic revision -m "description"  # New migration
pg_dump agriprofit > backup.sql                  # Backup

# Price Data Management
cd backend && python scripts/backfill_all_gaps.py --extend-to-today      # Fill ALL date gaps
cd backend && python scripts/backfill_prices.py --start-date 2026-01-20 --end-date 2026-02-17  # Targeted backfill
cd backend && python scripts/verify_price_coverage.py                    # Verify commodity coverage
cd backend && python scripts/audit_database_consistency.py               # Full DB audit
cd backend && python scripts/fill_missing_data.py                        # Fill gaps from audit report

# Docker (Production)
docker-compose -f docker-compose.prod.yml up -d                         # Start all services
```

## Scripts Reference (`backend/scripts/`)

| Script | Purpose |
|--------|---------|
| `backfill_all_gaps.py` | Comprehensive gap finder + backfill using historical API |
| `backfill_prices.py` | Historical backfill with BackfillClient/BackfillSeeder (reusable classes) |
| `verify_price_coverage.py` | Per-commodity date coverage verification (30/60/90 day windows) |
| `fill_missing_data.py` | Gap filler using historical resource (reads audit report) |
| `audit_database_consistency.py` | Full DB audit: gaps, coverage, quality, per-commodity analysis |
| `sync_now.py` | Manual trigger for daily data sync |
| `manage_db.py` | Database management utility (comprehensive) |
| `backfill_mandi_geocodes.py` | Add geocoding data to mandis |
| `etl_parquet_to_postgres.py` | Parquet to PostgreSQL data migration |
| `check_db_status.py` | Quick database status check |
| `list_indexes.py` | List all database indexes |
| `test_database_performance.py` | Database performance benchmarking |
| `test_query_performance.py` | Query performance testing |

## Data.gov.in API Integration

### Resources
| Resource | ID | Purpose |
|----------|-----|---------|
| Daily (current snapshot) | `9ef84268-d588-465a-a308-a864a43d0070` | Today's prices only |
| Historical (77M records) | `35985678-0d79-46b4-9ed6-6f13308a1d24` | Per-date historical data |

### API Key
`579b464db66ec23bdd000001d55108bb212f421a449b34595f56cb15`

### Key Details
- Base URL: `https://api.data.gov.in/resource/{resource_id}`
- Historical filter: `filters[Arrival_Date]` (MUST be capitalized)
- Date format: `dd/mm/YYYY` (e.g., `17/02/2026`)
- Pagination: limit=1000, offset-based
- Rate limiting: 5s between days, 2s between pages (to avoid 429s)
- Retry: exponential backoff up to 8 retries, extended waits for 429 errors
- Daily resource: used by `data_gov_client.py` for daily sync
- Historical resource: used by `backfill_prices.py` for gap backfilling

### Reusable Classes (from `backfill_prices.py`)
- **`BackfillClient`**: HTTP client for historical resource with pagination, retry, rate limiting
- **`BackfillSeeder`**: Bulk INSERT with ON CONFLICT for efficient deduplication, auto-creates commodities/mandis

## API Modules (113+ endpoints)

| Module | Prefix | Endpoints |
|--------|--------|-----------|
| Auth | `/auth` | 6 |
| Users | `/users` | 6 |
| Commodities | `/commodities` | 10 |
| Mandis | `/mandis` | 14 |
| Prices | `/prices` | 11 |
| Forecasts | `/forecasts` | 8 |
| Transport | `/transport` | 4 |
| Community | `/community/posts` | 17 |
| Notifications | `/notifications` | 10 |
| Admin | `/admin` | 6 |
| Analytics | `/analytics` | 11 |
| Inventory | `/inventory` | 4 |
| Sales | `/sales` | 4 |
| Uploads | `/uploads` | 2 |

## Middleware Stack

| Middleware | Purpose |
|-----------|---------|
| **RequestLogging** | Request IDs (UUID), slow request warnings (>1s), client IP detection |
| **SecurityMonitoring** | Auth failure tracking per IP, threshold alerting (3+ failures) |
| **ErrorLogging** | Unhandled exception logging with request context |
| **CORS** | Configured origins, credentials support |
| **RateLimiting** | slowapi with Redis (prod) or in-memory (dev) |

## Key Environment Variables

**Backend** (`backend/.env`):
```
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://agriprofit:agriprofit@localhost:5432/agriprofit
JWT_SECRET_KEY=dev-secret-key-not-for-production-use-32chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
OTP_LENGTH=6
OTP_COOLDOWN_SECONDS=2
TEST_OTP=123456
ENABLE_TEST_OTP=true
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
CORS_ALLOW_METHODS=["*"]
CORS_ALLOW_HEADERS=["*"]
ALLOWED_HOSTS=["*"]
DATA_GOV_API_KEY=579b464db66ec23bdd000001d55108bb212f421a449b34595f56cb15
DATA_GOV_RESOURCE_ID=9ef84268-d588-465a-a308-a864a43d0070
PRICE_SYNC_INTERVAL_HOURS=6
REDIS_URL=  (empty for dev, set for prod)
```

**Frontend** (`frontend/.env.local`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**Note:** `.env` file must use JSON arrays for list fields (`CORS_ORIGINS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`, `ALLOWED_HOSTS`) due to pydantic-settings v2 parsing. The `.env.development` template uses comma-separated values that don't work with the current pydantic-settings version.

## Docker Production Setup

```yaml
# docker-compose.prod.yml - 5 services
services:
  backend:    FastAPI + uvicorn on :8000
  frontend:   Next.js on :3000
  db:         PostgreSQL 15-alpine (not exposed externally)
  redis:      Redis alpine (not exposed externally)
  nginx:      Reverse proxy on :80/:443 with SSL
```

## What NOT to Change (stable, tested, working)

- Database schema (16 models, finalized)
- Authentication system (JWT + OTP)
- Data sync infrastructure (`app/integrations/`)
- API endpoint structure (113+ endpoints)
- Middleware stack (logging, security, rate limiting)

## Known Issues

- OTP mocked in dev (any 6-digit code works when `ENABLE_TEST_OTP=true`)
- Some date gaps in price_history are market holidays (expected)
- District neighbor mapping covers 12 states only (others fallback to same-district)
- Daily data.gov.in API resource only returns today's snapshot (use historical resource for backfilling)
- Frontend test coverage at 61.37% (598 tests, 100% pass rate)
- Pre-existing test failures in `test_prices_api.py` (404s due to route changes), `register/page.test.tsx`, `login/page.test.tsx`, `community/page.test.tsx`, `Sidebar.test.tsx`
- `conftest.py` SQLite schema must be manually kept in sync with SQLAlchemy models
- `.env.development` uses comma-separated lists that break pydantic-settings v2 JSON parsing

## Best Practices

### Database Queries
- Always use date-bounded queries on `price_history` (25M+ rows)
- Use `ORDER BY price_date DESC LIMIT 1` instead of `MAX(price_date)` for index efficiency
- Use `ON CONFLICT` for bulk upserts (see `BackfillSeeder.seed_day()`)
- Batch inserts in groups of 500 for optimal performance
- Use `reltuples` from `pg_class` for approximate counts

### Data Backfilling
- Always use the **historical** resource (`35985678-...`) not the daily one for gap filling
- Rate limit: 5s between days, 2s between pages to avoid 429 errors
- Use `--dry-run` first to see what would be fetched
- Verify with `verify_price_coverage.py` after backfilling
- `BackfillClient` and `BackfillSeeder` from `backfill_prices.py` are the canonical reusable classes

### Frontend Charts
- Always use `connectNulls` on Recharts `<Line>` components
- Generate continuous date ranges in memos (fill gaps with `undefined`)
- Use `MAX(price_date)` as reference for the date window, not `date.today()`
- Dynamic import all Recharts components with `{ ssr: false }`

### Testing
- Backend: `DATABASE_URL` env var required even for SQLite tests (config validation)
- Frontend: Mock next/navigation, next/dynamic, and all service modules
- Keep `conftest.py` table schemas in sync when adding model columns
- Use `vi.hoisted()` for mock variables referenced in `vi.mock()` factories
- Recharts components return `null` in test mocks (no need to render charts)

### Security
- Never expose Redis or PostgreSQL ports externally in production
- Use strong JWT secret (32+ chars) in production
- Rate limiting tiers prevent abuse: critical=5/min, write=30/min, read=100/min
- Auth failure tracking alerts after 3+ failures per IP
- All admin endpoints are logged with user context
