# AgriProfit Backend

FastAPI-based backend for the AgriProfit agricultural commodity price platform.

## Features

- 🚀 **Fast API:** Built with FastAPI for high performance async operations
- 🗄️ **PostgreSQL Database:** Scalable relational database with 32 performance indexes
- 🔄 **Automated Data Sync:** Updates commodity prices every 6 hours from data.gov.in
- 🔐 **JWT Authentication:** Secure user authentication with OTP verification
- 📊 **25M+ Price Records:** Historical commodity prices from 2003-present
- ⚡ **<200ms Queries:** Optimized with strategic database indexes
- 🔒 **Rate Limiting:** Per-user rate limits to prevent abuse
- 📝 **Community Features:** Forums, posts, replies, and likes
- 🔔 **Notifications:** Real-time user notifications
- 📈 **Forecasting:** ML-based price prediction (planned)

## Tech Stack

- **Framework:** FastAPI 0.104+
- **Database:** PostgreSQL 15+
- **ORM:** SQLAlchemy 2.0+
- **Validation:** Pydantic v2
- **Authentication:** JWT (python-jose)
- **Migrations:** Alembic
- **Scheduler:** APScheduler
- **Testing:** Pytest
- **Code Quality:** Ruff, Black

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Redis (optional, for caching)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/agriprofit.git
cd agriprofit/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Initial Data Load

```bash
# Option 1: Sync from data.gov.in API (requires API key)
export DATA_GOV_API_KEY=your_api_key_here
python -m app.cli sync-prices

# Option 2: Use ETL script if you have Parquet files
python scripts/etl_parquet_to_postgres.py

# Verify data loaded
python scripts/validate_migration.py
```

## Data Architecture

### Database Storage: PostgreSQL

All commodity price data is stored in PostgreSQL for:

- ✅ **Fast indexed queries** (<200ms average)
- ✅ **Concurrent access** (100+ simultaneous users)
- ✅ **ACID transactions**
- ✅ **Efficient aggregations**
- ✅ **Production-grade reliability**

### Core Tables

#### Price Data
- `commodities` - List of all tradeable crops (~400 items)
- `mandis` - Agricultural market yards (APMCs) (~3000 markets)
- `price_history` - Daily commodity prices (25M+ rows, main table)
- `price_forecasts` - ML-generated price predictions

#### User Management
- `users` - Registered farmers and traders
- `inventory` - User's crop inventory tracking
- `sales` - User's sales records and history
- `notifications` - User notification queue

#### Community
- `community_posts` - Forum discussions
- `community_replies` - Post replies
- `community_likes` - Like tracking

#### System
- `admin_actions` - Admin activity audit log
- `login_attempts` - Security tracking
- `otp_requests` - OTP verification logs

### Data Updates

**Automated Sync Service:**

- **Schedule:** Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
- **Source:** data.gov.in API (Government Open Data Platform)
- **Process:** Fetch → Validate → Deduplicate → Insert → Log
- **Monitoring:** `GET /sync/status` endpoint
- **Logs:** `logs/data_sync.log`

**Manual Sync:**

```bash
# Trigger immediate sync
python -m app.cli sync-prices

# Check sync status
curl http://localhost:8000/sync/status
```

### Performance Optimization

**32 Performance Indexes:**

- Price History: 6 indexes (commodity, mandi, date, composites)
- Commodities: 3 indexes (name search, category, active status)
- Mandis: 5 indexes (state, district, combinations)
- Community: 6 indexes (posts, replies, user lookups)
- Users: 4 indexes (location, role, status)
- Others: 8 indexes (inventory, sales, notifications)

**Query Performance:**

- Average query time: **180ms**
- P95 query time: **320ms**
- Date range queries: **4ms**
- Search queries: **3-5ms**

See [DATABASE_PERFORMANCE_INDEXES.md](DATABASE_PERFORMANCE_INDEXES.md) for details.

## API Endpoints

### Public Endpoints

```
GET  /health                    - Health check
GET  /docs                      - Interactive API documentation
GET  /commodities               - List all commodities
GET  /mandis                    - List all market yards
GET  /prices/latest             - Latest prices
GET  /community/posts           - Public forum posts
```

### Authenticated Endpoints

```
POST /auth/request-otp          - Request OTP for login
POST /auth/verify-otp           - Verify OTP and get token
GET  /auth/me                   - Get current user info

GET  /inventory                 - User's inventory
POST /inventory                 - Add inventory item
PUT  /inventory/{id}            - Update inventory

POST /sales                     - Record a sale
GET  /sales                     - User's sales history

POST /community/posts           - Create post
PUT  /community/posts/{id}      - Update post
POST /community/posts/{id}/reply - Reply to post
```

### Admin Endpoints

```
GET  /admin/users               - List all users
PUT  /admin/users/{id}/ban      - Ban/unban user
POST /admin/sync/trigger        - Trigger manual data sync
GET  /admin/actions             - View admin action log
```

See [API_CONTRACT.md](../API_CONTRACT.md) for complete API documentation.

## Project Structure

```
backend/
├── alembic/                  # Database migrations
│   └── versions/             # Migration files
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── admin/               # Admin management
│   ├── auth/                # Authentication & authorization
│   ├── commodities/         # Commodity endpoints
│   ├── community/           # Community forum
│   ├── core/                # Core utilities & config
│   ├── database/            # Database session & base
│   ├── integrations/        # External integrations
│   │   ├── data_sync.py    # Auto data sync service
│   │   └── scheduler.py    # APScheduler setup
│   ├── inventory/           # Inventory management
│   ├── mandis/              # Market yard endpoints
│   ├── models/              # SQLAlchemy models
│   ├── notifications/       # Notification system
│   ├── prices/              # Price query endpoints
│   ├── sales/               # Sales tracking
│   └── users/               # User management
├── scripts/                 # Utility scripts
│   ├── etl_parquet_to_postgres.py  # ETL migration
│   ├── validate_migration.py       # Data verification
│   ├── test_query_performance.py   # Performance testing
│   └── verify_migration_complete.py # Final checks
├── tests/                   # Test suite
├── logs/                    # Application logs
├── requirements.txt         # Python dependencies
├── alembic.ini             # Alembic configuration
├── pytest.ini              # Pytest configuration
└── .env                    # Environment variables (create from .env.example)
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_prices.py

# Run with verbose output
pytest -v
```

### Database Migrations

```bash
# Create a new migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current
```

### Code Quality

```bash
# Format code
black app/

# Lint
ruff check app/

# Type checking
mypy app/
```

### Performance Testing

```bash
# Test query performance
python scripts/test_query_performance.py

# List all indexes
python scripts/list_indexes.py

# Verify migration complete
python scripts/verify_migration_complete.py
```

## Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/agriprofit
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OTP Service (Twilio or Fast2SMS)
OTP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890

# Data Sync
PRICE_SYNC_ENABLED=true
PRICE_SYNC_INTERVAL_HOURS=6
DATA_GOV_API_KEY=your_data_gov_api_key

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Environment
ENVIRONMENT=development
DEBUG=true
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=false` in `.env`
- [ ] Set `ENVIRONMENT=production`
- [ ] Use strong `JWT_SECRET_KEY`
- [ ] Configure database backups
- [ ] Set up SSL/TLS certificates
- [ ] Configure reverse proxy (Nginx)
- [ ] Set up monitoring (Sentry, New Relic)
- [ ] Configure log rotation
- [ ] Set up automated database backups
- [ ] Test rollback procedure

### Docker Deployment

```bash
# Build image
docker build -t agriprofit-backend .

# Run container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  --name agriprofit-backend \
  agriprofit-backend
```

### Using Docker Compose

See `docker-compose.prod.yml` in root directory.

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Sync Status

```bash
curl http://localhost:8000/sync/status
```

### Logs

```bash
# View sync logs
tail -f logs/data_sync.log

# View application logs
tail -f logs/app.log
```

### Database Monitoring

```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('agriprofit'));

-- Check table sizes
SELECT 
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT * FROM pg_stat_user_indexes 
WHERE idx_scan = 0 AND indexname LIKE 'ix_%';
```

## Migration History

### v1.0.0 → v1.1.0 (Feb 2026)

**Major Change:** Migrated from Parquet files to PostgreSQL

**Benefits:**
- 166x faster queries
- 100+ concurrent users (vs. 2)
- Automated data updates every 6 hours
- 32 performance indexes

See [PARQUET_TO_POSTGRES_MIGRATION.md](PARQUET_TO_POSTGRES_MIGRATION.md) for details.

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql -U postgres -d agriprofit -c "SELECT 1"
```

### Slow Queries

```bash
# Run performance test
python scripts/test_query_performance.py

# Check if indexes are being used
psql -d agriprofit -c "EXPLAIN ANALYZE SELECT * FROM price_history LIMIT 100"
```

### Sync Service Not Running

```bash
# Check logs
tail -f logs/data_sync.log

# Verify scheduler is enabled
grep PRICE_SYNC_ENABLED .env

# Manual trigger
python -m app.cli sync-prices
```

## Support

- **Documentation:** See `/docs` folder
- **API Docs:** http://localhost:8000/docs (when running)
- **Issues:** GitHub Issues
- **Logs:** `backend/logs/`

## License

[Your License Here]

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

**Last Updated:** February 6, 2026  
**Version:** 1.1.0
