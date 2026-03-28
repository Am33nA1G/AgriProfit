# AgriProfit - Agricultural Commodity Price Tracking Platform

[![Tests](https://img.shields.io/badge/tests-598%20passing-brightgreen)](./frontend)
[![Coverage](https://img.shields.io/badge/coverage-61.37%25-brightgreen)](./frontend/coverage)
[![API](https://img.shields.io/badge/API-38ms%20avg-brightgreen)](./backend)
[![Production](https://img.shields.io/badge/status-ready-success)]()

> A production-grade SaaS platform helping farmers make data-driven decisions about commodity sales through real-time price tracking, ML-powered recommendations, and transport cost calculations.

## 🎯 Project Status: V1 Production Ready

**✅ Completed:**
- Full-stack application (FastAPI + Next.js)
- PostgreSQL database with optimized queries (38ms avg response)
- 598 automated tests (61.37% coverage)
- 142 manual test scenarios passed
- Admin dashboard with user management
- Mobile-responsive UI
- Cross-browser compatible

**🚀 Ready for deployment**

---

## 📋 Features

### Core Features
- **Real-time Price Tracking**: Live commodity prices across 500+ mandis
- **Smart Recommendations**: ML-powered analysis suggesting optimal selling strategies
- **Transport Calculator**: Accurate cost and profit calculations
- **Community Forum**: Farmer-to-farmer knowledge sharing
- **Inventory Management**: Track stock and sales with profit analysis
- **Admin Dashboard**: User management, content moderation, analytics

### Technical Highlights
- **Performance**: <40ms average API response time
- **Testing**: 598 automated tests, 142 manual test scenarios
- **Database**: PostgreSQL with optimized indexes
- **Real-time Updates**: Automatic data sync every 6 hours
- **Security**: JWT authentication, role-based access control

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ with SQLAlchemy 2.0
- **Authentication**: JWT tokens
- **API Performance**: 38ms average response time

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **UI**: Tailwind CSS, Radix UI components
- **State**: React hooks, Context API
- **Testing**: Vitest, React Testing Library (598 tests)

### Infrastructure
- **Data Sync**: Automated updates every 6 hours
- **Deployment**: Docker-ready (guides available)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Backend Setup
```bash
# 1. Clone repository
git clone [your-repo-url]
cd agriprofit

# 2. Create virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 5. Run database migrations
alembic upgrade head

# 6. Start server
uvicorn app.main:app --reload
# Backend running at http://localhost:8000
```

### Frontend Setup
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.local.example .env.local
# Edit .env.local with API URL

# 4. Start development server
npm run dev
# Frontend running at http://localhost:3000
```

### Run Tests
```bash
# Backend tests
cd backend
pytest --cov=app

# Frontend tests
cd frontend
npm test -- --coverage
```

---

## 📁 Project Structure
```
agriprofit/
├── backend/
│   ├── app/
│   │   ├── auth/           # Authentication
│   │   ├── commodities/    # Commodity management
│   │   ├── mandis/         # Mandi management
│   │   ├── transport/      # Transport calculator
│   │   ├── inventory/      # Inventory tracking
│   │   ├── sales/          # Sales logging
│   │   ├── community/      # Forum & posts
│   │   ├── admin/          # Admin features
│   │   └── main.py         # FastAPI app
│   ├── tests/              # Backend tests
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js pages (App Router)
│   │   ├── components/     # React components
│   │   ├── services/       # API clients
│   │   └── test/           # Test utilities
│   ├── __tests__/          # Frontend tests (598 tests)
│   └── package.json
│
└── docs/
    ├── DEPLOYMENT_GUIDE.md
    ├── API_DOCUMENTATION.md
    └── MANUAL_TEST_RESULTS.md
```

---

## 📖 Documentation

- **[Deployment Guide](./docs/DEPLOYMENT_GUIDE.md)**: Production setup instructions
- **[API Documentation](./docs/API_DOCUMENTATION.md)**: Complete API reference
- **[Testing Report](./frontend/TESTING_COMPLETE_FINAL.md)**: Coverage and test results
- **[Manual Test Results](./docs/MANUAL_TEST_RESULTS.md)**: 142 test scenarios

---

## 🔐 Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://user:password@localhost:5432/agriprofit
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
CORS_ORIGINS=http://localhost:3000
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🧪 Testing

### Backend Testing
- **Framework**: pytest
- **Coverage**: 100% API endpoints
- **Run**: `cd backend && pytest --cov=app`

### Frontend Testing
- **Framework**: Vitest + React Testing Library
- **Coverage**: 61.37% (598 tests)
- **Test Suites**: 38 files
- **Run**: `cd frontend && npm test`

---

## 🚀 Deployment

See [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) for detailed production deployment instructions including:
- Server setup
- Database configuration
- SSL/HTTPS setup
- Environment configuration
- Monitoring setup

---

## 📊 Performance Metrics

- **API Response Time**: 38ms average
- **Test Coverage**: 61.37% frontend, 100% backend API
- **Manual Tests**: 142/142 scenarios passed
- **Lighthouse Score**: 85+ performance

---

## 🤝 Contributing

This is a learning project. See issues for areas that could use improvement.

---

## 📄 License

[Your License]

---

## 👨‍💻 Author

[Your Name/Team]

**Project Status**: V1 Production Ready ✅  
**Last Updated**: February 2026