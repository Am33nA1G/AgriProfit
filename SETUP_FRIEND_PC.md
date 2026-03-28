# AgriProfit - Complete Setup Guide for Friend's PC

This guide walks through installing and running the entire AgriProfit stack on a new machine.

## 🖥️ System Requirements

- **OS**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Python**: 3.11 or higher
- **Node.js**: 18+ (includes npm)
- **PostgreSQL**: 15+ 
- **Git**: Latest version
- **RAM**: 8GB minimum (16GB recommended)
- **Disk Space**: 5GB+ free space

## 📦 Installation Steps

### Step 1: Install Prerequisites

#### Windows
1. **Python**: Download from https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
   - Verify: Open Command Prompt and run `python --version`

2. **Node.js**: Download from https://nodejs.org (LTS version recommended)
   - Verify: `node --version` and `npm --version`

3. **PostgreSQL**: Download from https://www.postgresql.org/download/
   - During installation, set a password for the `postgres` user (remember this!)
   - Note the port (default: 5432)
   - Verify: `psql --version`

4. **Git**: Download from https://git-scm.com/download/win
   - Verify: `git --version`

#### macOS (using Homebrew)
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install prerequisites
brew install python@3.11 node postgresql git
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv nodejs postgresql git
```

---

### Step 2: Clone the Repository

```bash
git clone [your-repo-url]
cd repo-root
```

---

### Step 3: Setup Database

#### Windows (Command Prompt or PowerShell)
```bash
# Connect to PostgreSQL
psql -U postgres

# In psql prompt, run:
CREATE DATABASE agriprofit;
CREATE USER agriprofit_user WITH PASSWORD 'secure_password_123';
ALTER ROLE agriprofit_user SET client_encoding TO 'utf8';
ALTER ROLE agriprofit_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE agriprofit_user SET default_transaction_deferrable TO on;
ALTER ROLE agriprofit_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE agriprofit TO agriprofit_user;
\q
```

#### macOS/Linux
```bash
# Same as Windows - use psql command above
psql -U postgres
# Follow the same SQL commands
```

---

### Step 4: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with database credentials
```

#### Configure Backend `.env` File
Create `backend/.env` with:
```env
# Database
DATABASE_URL=postgresql://agriprofit_user:secure_password_123@localhost:5432/agriprofit
SQLALCHEMY_ECHO=False

# JWT
SECRET_KEY=your_secret_key_generate_random_string_here
ALGORITHM=HS256

# API
API_V1_STR=/api/v1
DEBUG=True
CORS_ORIGINS=["http://localhost:3000","http://localhost:8081","http://localhost:5173"]

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Data.gov API (optional)
DATA_GOV_API_KEY=your_api_key_here

# Sentry (optional)
SENTRY_DSN=
```

#### Run Database Migrations
```bash
alembic upgrade head
```

#### (Optional) Load Sample Data
```bash
# If you have parquet files:
python scripts/etl_parquet_to_postgres.py

# Or verify database:
python scripts/check_db_status.py
```

#### Start Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be at: **http://localhost:8000**  
API Docs at: **http://localhost:8000/docs**

---

### Step 5: Frontend Setup

```bash
# Open new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env.local
```

#### Configure Frontend `.env.local`
Create `frontend/.env.local` with:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=AgriProfit
```

#### Start Frontend Server
```bash
npm run dev
```

Frontend will be at: **http://localhost:3000**

---

### Step 6: Mobile App Setup (Optional)

```bash
# Open new terminal, navigate to mobile
cd mobile

# Install dependencies (if not already done)
npm install

# Create/verify .env file
```

#### Mobile `.env` (should already exist)
```env
EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1
EXPO_PUBLIC_ENV=development
```

#### Start Mobile App
```bash
# Option 1: Web preview
npx expo start --web
# Open http://localhost:19006

# Option 2: Android emulator (requires Android Studio)
npx expo start --android

# Option 3: iOS simulator (macOS only)
npx expo start --ios

# Option 4: On physical device
npx expo start
# Scan QR code with Expo Go app
```

---

## 🚀 Quick Start Script (All-in-One)

For easier setup, create a script file:

### Windows: `start-all.ps1`
```powershell
# Backend
Start-Process powershell -ArgumentList "cd backend; venv\Scripts\activate; uvicorn app.main:app --reload"

# Frontend  
Start-Process powershell -ArgumentList "cd frontend; npm run dev"

# Mobile (optional)
Start-Process powershell -ArgumentList "cd mobile; npx expo start --web"

Write-Host "All services starting..."
Write-Host "Backend:  http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
Write-Host "Mobile:   http://localhost:19006"
```

Run with: `.\start-all.ps1`

### macOS/Linux: `start-all.sh`
```bash
#!/bin/bash

# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload &

# Frontend
cd ../frontend
npm run dev &

# Mobile (optional)
cd ../mobile
npx expo start --web &

echo "All services starting..."
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Mobile:   http://localhost:19006"
```

Run with: `chmod +x start-all.sh && ./start-all.sh`

---

## 📋 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Backend API** | http://localhost:8000 | REST API server |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **Frontend** | http://localhost:3000 | Web application |
| **Mobile (Web)** | http://localhost:19006 | Mobile app preview |

---

## 🔧 Troubleshooting

### Backend won't start
```bash
# Clear cache and reinstall
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

# Check database connection
python scripts/check_db_status.py
```

### Frontend won't start
```bash
# Clear cache
rm -rf .next node_modules
npm install
npm run dev
```

### Database connection issues
```bash
# Verify PostgreSQL is running
# Windows: Services app → PostgreSQL
# Mac/Linux: 
brew services list  # macOS
sudo systemctl status postgresql  # Linux

# Test connection:
psql -U agriprofit_user -d agriprofit -h localhost -p 5432
```

### Port conflicts (e.g., port 3000 already in use)
```bash
# Backend: Change port in startup
uvicorn app.main:app --reload --port 8001

# Frontend: Set in .env.local
PORT=3001
```

---

## 🧪 Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Frontend tests with coverage
npm run test:coverage
```

---

## 📚 Next Steps

1. **Explore API Docs**: Visit http://localhost:8000/docs
2. **Create Account**: Sign up on the frontend
3. **Check Database**: `psql` commands in `backend/scripts/`
4. **Read Full Docs**: 
   - [API Documentation](docs/API_DOCUMENTATION.md)
   - [System Architecture](docs/SYSTEM_ARCHITECTURE.md)
   - [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)

---

## 💡 Tips for Your Friend

1. **Keep terminals organized**: Use tab names or separate windows
2. **Monitor logs**: Check terminal output for errors
3. **Database backups**: Regularly backup PostgreSQL data
4. **API testing**: Use Postman/Insomnia for API testing
5. **Hot reload**: Both frontend and backend auto-reload on file changes

---

## 🆘 Still Having Issues?

1. Check the error logs in the terminal
2. Verify all prerequisites are installed: `python --version`, `node --version`, `psql --version`
3. Ensure database is running and credentials are correct
4. Check that ports 8000, 3000, 5432 are not in use
5. Review the [full documentation](docs/) for more details

---

**Happy coding! 🚀**
