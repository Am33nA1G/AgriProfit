# AgriProfit V1 - Quick Start Guide

A rapid setup guide to get the development environment running.

---

## Prerequisites

- **Python 3.11+** (backend)
- **Node.js 18+** (frontend)
- **PostgreSQL 15+** (database)
- **Git** (version control)

---

## 1. Clone & Setup

```bash
# Clone the repository
git clone <repository-url>
cd repo-root
```

---

## 2. Backend Setup

### 2.1 Create Virtual Environment

```bash
cd backend

# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2.2 Install Dependencies

```bash
pip install -r requirements.txt
```

### 2.3 Configure Environment

```bash
# Copy the example environment file
cp .env.example .env.development

# Edit .env.development with your database credentials
# Key variables to set:
#   DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/agriprofit
#   JWT_SECRET_KEY=<generate-32-char-secret>
```

**Generate JWT Secret:**
```bash
# Windows PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

# macOS/Linux
openssl rand -hex 32
```

### 2.4 Setup Database

```bash
# Create database in PostgreSQL
psql -U postgres
CREATE DATABASE agriprofit;
\q

# Run migrations
alembic upgrade head
```

### 2.5 Start Backend Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will be available at:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 3. Frontend Setup

### 3.1 Install Dependencies

```bash
cd frontend
npm install
```

### 3.2 Configure Environment

Create a `.env.local` file:

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3.3 Start Frontend Server

```bash
npm run dev
```

**Frontend will be available at:**
- App: http://localhost:3000

---

## 4. Running Tests

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_auth_api.py -v

# Run tests matching a pattern
pytest -k "test_auth" -v
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage
```

---

## 5. Common Development Tasks

### Seed Database with Sample Data

```bash
cd backend
python -m app.cli seed
```

### Create New Alembic Migration

```bash
cd backend
alembic revision --autogenerate -m "description_of_changes"
alembic upgrade head
```

### Check Backend Logs

Logs are written to `backend/logs/` directory:
- `app.log` - Application logs
- `access.log` - Request logs

### Lint Frontend Code

```bash
cd frontend
npm run lint
```

### Build Frontend for Production

```bash
cd frontend
npm run build
npm start
```

---

## 6. Quick API Testing

### Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"1.0.0"}
```

### Request OTP (Development Mode)

```bash
curl -X POST http://localhost:8000/api/v1/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "9876543210"}'
```

In development mode, the OTP is logged to console (not sent via SMS).

### Verify OTP

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"request_id": "<from-previous-response>", "otp": "<from-logs>"}'
```

---

## 7. Project Structure

```
repo-root/
├── backend/
│   ├── app/
│   │   ├── auth/           # Authentication module
│   │   ├── commodities/    # Commodities module
│   │   ├── community/      # Community posts
│   │   ├── core/           # Config, middleware, logging
│   │   ├── database/       # SQLAlchemy setup
│   │   ├── models/         # Database models
│   │   ├── ...             # Other modules
│   │   └── main.py         # FastAPI app entry point
│   ├── alembic/            # Database migrations
│   ├── tests/              # Backend tests
│   ├── .env.example        # Environment template
│   └── requirements.txt    # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js pages (App Router)
│   │   ├── components/     # React components
│   │   ├── services/       # API service files
│   │   ├── hooks/          # Custom React hooks
│   │   ├── store/          # Zustand stores
│   │   └── lib/            # Utilities
│   ├── package.json        # Node dependencies
│   └── next.config.ts      # Next.js config
│
├── API_CONTRACT.md         # API specification
├── PRODUCT_CONTRACT.md     # Product requirements
└── PROJECT_STATUS_REPORT.md # Current status
```

---

## 8. Known Issues & Workarounds

### Issue 1: Database Connection Refused

**Symptom:** `Connection refused` when starting backend

**Fix:**
1. Ensure PostgreSQL is running
2. Verify `DATABASE_URL` in `.env.development`
3. Check that the database exists:
   ```bash
   psql -U postgres -c "\l" | grep agriprofit
   ```

### Issue 2: CORS Errors in Browser

**Symptom:** API calls blocked by CORS policy

**Fix:**
1. Verify `CORS_ORIGINS` in backend `.env` includes frontend URL
2. Ensure frontend is accessing correct API URL
3. Check that backend is running

### Issue 3: Frontend Build Fails on TypeScript

**Symptom:** Type errors during `npm run build`

**Fix:**
```bash
# Check for type errors
npx tsc --noEmit

# If issues persist, try clean install
rm -rf node_modules package-lock.json
npm install
```

### Issue 4: Alembic Migration Conflicts

**Symptom:** Multiple migration heads

**Fix:**
```bash
alembic heads  # Check for multiple heads
alembic merge -m "merge heads" <head1> <head2>
alembic upgrade head
```

### Issue 5: Test Database Pollution

**Symptom:** Tests failing due to stale data

**Fix:**
Tests use a separate test database. Ensure `conftest.py` fixtures clean up properly:
```bash
pytest --tb=short  # See which tests are failing
```

---

## 9. Environment Variables Reference

### Backend (Required)

| Variable | Example | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | dev/staging/production |
| `DATABASE_URL` | `postgresql+psycopg://...` | Database connection |
| `JWT_SECRET_KEY` | `<32+ chars>` | Token signing key |

### Backend (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `true` | Enable debug mode |
| `OTP_LENGTH` | `6` | OTP code length |
| `OTP_EXPIRE_MINUTES` | `5` | OTP validity |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level |

### Frontend

| Variable | Example | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Backend API URL |

---

## 10. Useful Commands Cheatsheet

```bash
# Backend
cd backend
uvicorn app.main:app --reload          # Start dev server
pytest                                  # Run tests
alembic upgrade head                   # Apply migrations
alembic downgrade -1                   # Rollback one migration

# Frontend
cd frontend
npm run dev                            # Start dev server
npm run build                          # Production build
npm test                               # Run tests
npm run lint                           # Lint code

# Database
psql -U postgres -d agriprofit         # Connect to DB
alembic current                        # Current migration
alembic history                        # Migration history
```

---

## 11. Getting Help

- **API Documentation:** http://localhost:8000/docs
- **Product Requirements:** See `PRODUCT_CONTRACT.md`
- **API Specification:** See `API_CONTRACT.md`
- **Current Status:** See `PROJECT_STATUS_REPORT.md`

---

## 12. Next Steps After Setup

1. **Explore the API** - Open http://localhost:8000/docs
2. **Test the Login Flow** - Use the frontend at http://localhost:3000/login
3. **Check the Dashboard** - Navigate to /dashboard after login
4. **Run the Test Suite** - Verify everything works with `pytest` and `npm test`

---

*Happy coding! If you encounter issues not covered here, check the PROJECT_STATUS_REPORT.md for known issues.*
