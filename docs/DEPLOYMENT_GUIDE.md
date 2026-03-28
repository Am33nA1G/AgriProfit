# AgriProfit V1 - Production Deployment Guide

**Version**: 1.0  
**Last Updated**: February 2026  
**Deployment Target**: Ubuntu 22.04 LTS  

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Database Setup](#database-setup)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Nginx Configuration](#nginx-configuration)
7. [SSL Certificate Setup](#ssl-certificate-setup)
8. [Data Sync Service](#data-sync-service)
9. [Security Checklist](#security-checklist)
10. [Monitoring & Maintenance](#monitoring--maintenance)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Server Requirements

**Minimum Specifications:**
- **OS**: Ubuntu 22.04 LTS (recommended) or 20.04 LTS
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 40GB SSD
- **Network**: Public IP address

**Recommended for Production:**
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 100GB SSD

### Required Services

- PostgreSQL 15+
- Python 3.11+
- Node.js 18+ (LTS)
- Nginx
- Certbot (for SSL)

### Domain & DNS

- Domain name registered (e.g., `agriprofit.com`)
- DNS A record pointing to server IP:
  - `@` → `<server-ip>` (for agriprofit.com)
  - `api` → `<server-ip>` (for api.agriprofit.com)

---

## Server Setup

### 1. Update System Packages

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y build-essential git curl wget vim ufw
```

### 2. Configure Firewall (UFW)

```bash
# Enable UFW
sudo ufw enable

# Allow SSH (important: do this first!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status verbose
```

**Expected Output:**
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

### 3. Create Application User

```bash
# Create user for running the application
sudo adduser --system --group --home /opt/agriprofit agriprofit

# Add to sudoers (optional, for maintenance)
sudo usermod -aG sudo agriprofit
```

---

## Database Setup

### 1. Install PostgreSQL

```bash
# Install PostgreSQL 15
sudo apt install -y postgresql-15 postgresql-contrib-15

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Check status
sudo systemctl status postgresql
```

### 2. Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# Inside PostgreSQL shell:
CREATE DATABASE agriprofit;
CREATE USER agriprofit_user WITH ENCRYPTED PASSWORD 'your-strong-password-here';
GRANT ALL PRIVILEGES ON DATABASE agriprofit TO agriprofit_user;
ALTER DATABASE agriprofit OWNER TO agriprofit_user;

# Exit PostgreSQL
\q
```

**Important**: Replace `your-strong-password-here` with a strong password (32+ characters).

### 3. Configure PostgreSQL

```bash
# Edit PostgreSQL configuration
sudo vim /etc/postgresql/15/main/postgresql.conf
```

**Add/modify these settings:**
```conf
# Connection Settings
listen_addresses = 'localhost'  # Only allow local connections
max_connections = 100

# Memory Settings
shared_buffers = 256MB          # 25% of RAM for 1GB, adjust for your server
effective_cache_size = 1GB      # 50-75% of RAM
work_mem = 16MB
maintenance_work_mem = 64MB

# Performance
random_page_cost = 1.1          # For SSD
effective_io_concurrency = 200  # For SSD
```

**Restart PostgreSQL:**
```bash
sudo systemctl restart postgresql
```

### 4. Test Database Connection

```bash
# Test connection
psql -h localhost -U agriprofit_user -d agriprofit

# Inside PostgreSQL shell:
\conninfo
\q
```

---

## Backend Deployment

### 1. Install Python 3.11

```bash
# Add deadsnakes PPA (if Python 3.11 not in default repos)
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Verify installation
python3.11 --version
```

### 2. Clone Repository

```bash
# Switch to agriprofit user
sudo su - agriprofit

# Clone repository
cd /opt/agriprofit
git clone https://github.com/your-username/agriprofit.git app
cd app/backend

# Or if using a different deployment method, upload your code here
```

### 3. Setup Python Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install production server
pip install gunicorn
```

### 4. Configure Environment Variables

```bash
# Create production .env file
vim /opt/agriprofit/app/backend/.env
```

**Production `.env` file:**
```env
# Database
DATABASE_URL=postgresql://agriprofit_user:your-strong-password-here@localhost:5432/agriprofit

# Security
SECRET_KEY=your-64-character-random-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# CORS (IMPORTANT: Use your actual domain)
CORS_ORIGINS=https://agriprofit.com,https://www.agriprofit.com

# Environment
ENVIRONMENT=production
DEBUG=false

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Optional: Test OTP for development
# TEST_OTP=123456
```

**Generate a secure SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 5. Run Database Migrations

```bash
# Activate virtual environment
source /opt/agriprofit/app/backend/venv/bin/activate

# Run migrations
cd /opt/agriprofit/app/backend
alembic upgrade head

# Verify tables created
psql -h localhost -U agriprofit_user -d agriprofit -c "\dt"
```

### 6. Create Systemd Service

**Create service file:**
```bash
sudo vim /etc/systemd/system/agriprofit-api.service
```

**Service configuration:**
```ini
[Unit]
Description=AgriProfit FastAPI Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=agriprofit
Group=agriprofit
WorkingDirectory=/opt/agriprofit/app/backend
Environment="PATH=/opt/agriprofit/app/backend/venv/bin"
ExecStart=/opt/agriprofit/app/backend/venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /opt/agriprofit/logs/access.log \
    --error-logfile /opt/agriprofit/logs/error.log \
    --log-level info \
    app.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Create log directory:**
```bash
sudo mkdir -p /opt/agriprofit/logs
sudo chown agriprofit:agriprofit /opt/agriprofit/logs
```

**Enable and start service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable agriprofit-api.service

# Start service
sudo systemctl start agriprofit-api.service

# Check status
sudo systemctl status agriprofit-api.service

# View logs
sudo journalctl -u agriprofit-api.service -f
```

### 7. Test Backend API

```bash
# Test API is running
curl http://localhost:8000/docs

# Should return HTML for Swagger UI

# Test health endpoint (if you have one)
curl http://localhost:8000/health
```

---

## Frontend Deployment

### 1. Install Node.js

```bash
# Install Node.js 18 LTS using NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version  # Should show v18.x.x
npm --version
```

### 2. Build Frontend

```bash
# Navigate to frontend directory
cd /opt/agriprofit/app/frontend

# Create production .env.local
vim .env.local
```

**Production `.env.local`:**
```env
NEXT_PUBLIC_API_URL=https://api.agriprofit.com
```

**Install dependencies and build:**
```bash
# Install dependencies
npm ci --production=false

# Build for production
npm run build

# Test build locally (optional)
npm start
```

### 3. Setup Frontend Directory

```bash
# Create web directory
sudo mkdir -p /var/www/agriprofit

# Copy build files
sudo cp -r /opt/agriprofit/app/frontend/.next /var/www/agriprofit/
sudo cp -r /opt/agriprofit/app/frontend/public /var/www/agriprofit/
sudo cp /opt/agriprofit/app/frontend/package*.json /var/www/agriprofit/
sudo cp /opt/agriprofit/app/frontend/.env.local /var/www/agriprofit/

# Install production dependencies only
cd /var/www/agriprofit
sudo npm ci --production

# Set ownership
sudo chown -R agriprofit:agriprofit /var/www/agriprofit
```

### 4. Create Next.js Systemd Service

**Create service file:**
```bash
sudo vim /etc/systemd/system/agriprofit-frontend.service
```

**Service configuration:**
```ini
[Unit]
Description=AgriProfit Next.js Frontend
After=network.target

[Service]
Type=simple
User=agriprofit
Group=agriprofit
WorkingDirectory=/var/www/agriprofit
Environment="NODE_ENV=production"
Environment="PORT=3000"
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable agriprofit-frontend.service

# Start service
sudo systemctl start agriprofit-frontend.service

# Check status
sudo systemctl status agriprofit-frontend.service

# View logs
sudo journalctl -u agriprofit-frontend.service -f
```

---

## Nginx Configuration

### 1. Install Nginx

```bash
# Install Nginx
sudo apt install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Check status
sudo systemctl status nginx
```

### 2. Configure Nginx

**Create site configuration:**
```bash
sudo vim /etc/nginx/sites-available/agriprofit
```

**Nginx configuration:**
```nginx
# HTTP - Redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name agriprofit.com www.agriprofit.com api.agriprofit.com;
    
    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# Frontend - HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name agriprofit.com www.agriprofit.com;
    
    # SSL Configuration (will be added by Certbot)
    # ssl_certificate /etc/letsencrypt/live/agriprofit.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/agriprofit.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Proxy to Next.js
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Static files caching
    location /_next/static {
        proxy_pass http://localhost:3000;
        proxy_cache_valid 200 365d;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
}

# Backend API - HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.agriprofit.com;
    
    # SSL Configuration (will be added by Certbot)
    # ssl_certificate /etc/letsencrypt/live/api.agriprofit.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/api.agriprofit.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint (no auth required)
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
```

**Enable site:**
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/agriprofit /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## SSL Certificate Setup

### 1. Install Certbot

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Create directory for Certbot challenges
sudo mkdir -p /var/www/certbot
```

### 2. Obtain SSL Certificates

```bash
# Get certificate for main domain
sudo certbot --nginx -d agriprofit.com -d www.agriprofit.com

# Get certificate for API subdomain
sudo certbot --nginx -d api.agriprofit.com

# Follow prompts:
# - Enter email address
# - Agree to terms of service
# - Choose whether to redirect HTTP to HTTPS (recommended: Yes)
```

### 3. Test Auto-Renewal

```bash
# Test renewal (dry run)
sudo certbot renew --dry-run

# Certbot will automatically renew certificates before expiry
# Cron job is created automatically at /etc/cron.d/certbot
```

### 4. Verify SSL

```bash
# Check certificate details
sudo certbot certificates

# Test SSL configuration
curl -I https://agriprofit.com
curl -I https://api.agriprofit.com
```

---

## Data Sync Service

### 1. Create Sync Script

```bash
# Create script
sudo vim /opt/agriprofit/scripts/sync_data.sh
```

**Sync script:**
```bash
#!/bin/bash

# Data sync script for AgriProfit
# Runs data update from government APIs

LOG_FILE="/opt/agriprofit/logs/sync.log"
BACKEND_DIR="/opt/agriprofit/app/backend"
VENV_PATH="$BACKEND_DIR/venv/bin/activate"

# Log function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Starting data sync..."

# Activate virtual environment
source "$VENV_PATH"

# Run sync command (adjust based on your CLI command)
cd "$BACKEND_DIR"
python -m app.cli sync-prices >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "Data sync completed successfully"
else
    log "ERROR: Data sync failed"
    exit 1
fi

log "Sync finished"
```

**Make executable:**
```bash
sudo chmod +x /opt/agriprofit/scripts/sync_data.sh
sudo chown agriprofit:agriprofit /opt/agriprofit/scripts/sync_data.sh
```

### 2. Setup Cron Job

```bash
# Edit crontab for agriprofit user
sudo crontab -u agriprofit -e
```

**Add cron job (runs every 6 hours):**
```cron
# AgriProfit data sync - every 6 hours
0 */6 * * * /opt/agriprofit/scripts/sync_data.sh

# Alternative: specific times (2 AM, 8 AM, 2 PM, 8 PM)
# 0 2,8,14,20 * * * /opt/agriprofit/scripts/sync_data.sh
```

### 3. Test Sync Manually

```bash
# Run sync script manually
sudo -u agriprofit /opt/agriprofit/scripts/sync_data.sh

# Check logs
tail -f /opt/agriprofit/logs/sync.log
```

---

## Security Checklist

### ✅ Pre-Deployment Security Review

- [ ] **Strong Passwords**
  - [ ] PostgreSQL password: 32+ characters, random
  - [ ] JWT SECRET_KEY: 64+ characters, random
  - [ ] Server user passwords: 20+ characters

- [ ] **Environment Variables**
  - [ ] No secrets in code repository
  - [ ] `.env` file has correct permissions (600)
  - [ ] CORS origins restricted to production domain only
  - [ ] DEBUG mode disabled (`DEBUG=false`)

- [ ] **Database Security**
  - [ ] PostgreSQL only listens on localhost
  - [ ] Database user has minimal permissions
  - [ ] Regular backups configured
  - [ ] No default passwords

- [ ] **Firewall Configuration**
  - [ ] UFW enabled
  - [ ] Only ports 22, 80, 443 open
  - [ ] SSH port 22 accessible (or custom port if changed)
  - [ ] PostgreSQL port 5432 NOT exposed to internet

- [ ] **SSL/TLS**
  - [ ] SSL certificates installed
  - [ ] HTTPS enforced (HTTP redirects to HTTPS)
  - [ ] Strong cipher suites configured
  - [ ] HSTS header enabled

- [ ] **Application Security**
  - [ ] CORS configured correctly
  - [ ] Rate limiting enabled (if implemented)
  - [ ] Input validation on all endpoints
  - [ ] SQL injection protection (SQLAlchemy ORM used)
  - [ ] XSS protection headers set

- [ ] **Server Security**
  - [ ] System packages updated
  - [ ] Automatic security updates enabled
  - [ ] SSH key-based authentication (password auth disabled)
  - [ ] Fail2ban installed (optional but recommended)

### Setup Automatic Security Updates

```bash
# Install unattended-upgrades
sudo apt install -y unattended-upgrades

# Enable automatic security updates
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Verify configuration
sudo systemctl status unattended-upgrades
```

### Optional: Install Fail2ban

```bash
# Install Fail2ban
sudo apt install -y fail2ban

# Configure for SSH protection
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo vim /etc/fail2ban/jail.local

# Enable and start
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check status
sudo fail2ban-client status sshd
```

---

## Monitoring & Maintenance

### 1. Log Monitoring

**View application logs:**
```bash
# Backend API logs
sudo journalctl -u agriprofit-api.service -f

# Frontend logs
sudo journalctl -u agriprofit-frontend.service -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Data sync logs
tail -f /opt/agriprofit/logs/sync.log
```

### 2. Database Backups

**Create backup script:**
```bash
sudo vim /opt/agriprofit/scripts/backup_db.sh
```

**Backup script:**
```bash
#!/bin/bash

BACKUP_DIR="/opt/agriprofit/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/agriprofit_$DATE.sql.gz"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Backup database
pg_dump -h localhost -U agriprofit_user agriprofit | gzip > "$BACKUP_FILE"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "agriprofit_*.sql.gz" -mtime +7 -delete

echo "Backup created: $BACKUP_FILE"
```

**Make executable and schedule:**
```bash
# Make executable
sudo chmod +x /opt/agriprofit/scripts/backup_db.sh
sudo chown agriprofit:agriprofit /opt/agriprofit/scripts/backup_db.sh

# Add to crontab (daily at 2 AM)
sudo crontab -u agriprofit -e

# Add line:
0 2 * * * /opt/agriprofit/scripts/backup_db.sh
```

### 3. Disk Space Monitoring

```bash
# Check disk usage
df -h

# Check specific directories
du -sh /opt/agriprofit/*
du -sh /var/www/agriprofit/*
du -sh /var/log/nginx/*
```

### 4. Setup Log Rotation

**Create logrotate configuration:**
```bash
sudo vim /etc/logrotate.d/agriprofit
```

**Logrotate config:**
```
/opt/agriprofit/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0640 agriprofit agriprofit
}
```

### 5. Performance Monitoring

**Monitor system resources:**
```bash
# CPU and memory usage
htop

# Disk I/O
iotop

# Network connections
netstat -tuln | grep LISTEN

# PostgreSQL connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

### 6. API Uptime Monitoring

**Use external monitoring service (recommended):**
- UptimeRobot (free tier available)
- Pingdom
- StatusCake
- New Relic

**Monitor these endpoints:**
- `https://agriprofit.com` (Frontend)
- `https://api.agriprofit.com/health` (Backend health)
- `https://api.agriprofit.com/docs` (API docs)

---

## Troubleshooting

### API Returns 502 Bad Gateway

**Symptoms:** Nginx returns 502 when accessing API

**Diagnosis:**
```bash
# Check if FastAPI service is running
sudo systemctl status agriprofit-api.service

# Check backend logs
sudo journalctl -u agriprofit-api.service -n 50
```

**Solutions:**
```bash
# Restart backend service
sudo systemctl restart agriprofit-api.service

# Check if port 8000 is in use
sudo netstat -tlnp | grep 8000

# If another process is using port 8000, kill it
sudo kill <PID>
```

---

### Database Connection Errors

**Symptoms:** API logs show "connection refused" or "authentication failed"

**Diagnosis:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
psql -h localhost -U agriprofit_user -d agriprofit

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

**Solutions:**
```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Verify credentials in .env file
cat /opt/agriprofit/app/backend/.env | grep DATABASE_URL

# Check PostgreSQL is listening
sudo netstat -tlnp | grep 5432
```

---

### Frontend Shows 404 Errors

**Symptoms:** Pages return 404, blank pages, or "Page Not Found"

**Diagnosis:**
```bash
# Check if Next.js service is running
sudo systemctl status agriprofit-frontend.service

# Check frontend logs
sudo journalctl -u agriprofit-frontend.service -n 50

# Check Nginx configuration
sudo nginx -t
```

**Solutions:**
```bash
# Restart frontend service
sudo systemctl restart agriprofit-frontend.service

# Rebuild frontend
cd /opt/agriprofit/app/frontend
npm run build
sudo cp -r .next /var/www/agriprofit/

# Restart Nginx
sudo systemctl restart nginx
```

---

### Slow API Response Times

**Symptoms:** API endpoints take >1000ms to respond

**Diagnosis:**
```bash
# Check database query performance
sudo -u postgres psql agriprofit -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check server load
htop

# Check PostgreSQL connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solutions:**
```bash
# Add database indexes (check backend migrations)
# Increase PostgreSQL shared_buffers
# Add more worker processes to Gunicorn
# Upgrade server resources

# Optimize Gunicorn workers
sudo vim /etc/systemd/system/agriprofit-api.service
# Adjust --workers to (2 * CPU_CORES) + 1
```

---

### SSL Certificate Issues

**Symptoms:** Browser shows "Not Secure" or certificate errors

**Diagnosis:**
```bash
# Check certificate status
sudo certbot certificates

# Check Nginx SSL configuration
sudo nginx -t

# Test SSL
curl -I https://agriprofit.com
```

**Solutions:**
```bash
# Renew certificates manually
sudo certbot renew

# Force renewal
sudo certbot renew --force-renewal

# Check Nginx SSL configuration
sudo vim /etc/nginx/sites-available/agriprofit
```

---

### Data Sync Not Running

**Symptoms:** Prices not updating, stale data in database

**Diagnosis:**
```bash
# Check cron jobs
sudo crontab -u agriprofit -l

# Check sync logs
tail -f /opt/agriprofit/logs/sync.log

# Check if script is executable
ls -l /opt/agriprofit/scripts/sync_data.sh
```

**Solutions:**
```bash
# Run sync manually to test
sudo -u agriprofit /opt/agriprofit/scripts/sync_data.sh

# Verify cron job syntax
sudo crontab -u agriprofit -e

# Check script permissions
sudo chmod +x /opt/agriprofit/scripts/sync_data.sh
```

---

### Out of Disk Space

**Symptoms:** 500 errors, database write failures, service crashes

**Diagnosis:**
```bash
# Check disk usage
df -h

# Find large files
sudo du -h /opt/agriprofit | sort -rh | head -n 20
sudo du -h /var/log | sort -rh | head -n 20
```

**Solutions:**
```bash
# Clean old logs
sudo journalctl --vacuum-time=7d

# Clean old backups
find /opt/agriprofit/backups -mtime +30 -delete

# Rotate Nginx logs
sudo logrotate -f /etc/logrotate.d/nginx

# Clean package cache
sudo apt clean
```

---

## Post-Deployment Checklist

### ✅ Verification Steps

- [ ] **Frontend loads**: Visit https://agriprofit.com
- [ ] **API accessible**: Visit https://api.agriprofit.com/docs
- [ ] **SSL working**: No browser warnings
- [ ] **Login works**: Test registration and login flow
- [ ] **Database populated**: Check mandis and commodities data
- [ ] **Data sync runs**: Check sync logs after 6 hours
- [ ] **Backups working**: Verify daily backup creation
- [ ] **Monitoring active**: Uptime monitoring configured
- [ ] **Logs rotating**: Check logrotate configuration
- [ ] **Firewall active**: `sudo ufw status` shows enabled
- [ ] **Services auto-start**: Reboot server and verify all services start

### Test the Complete Flow

1. Register new user
2. Complete profile
3. Add inventory item
4. View commodities and prices
5. Use transport calculator
6. Create community post
7. Login as admin
8. Verify admin dashboard

---

## Quick Reference Commands

```bash
# Start all services
sudo systemctl start agriprofit-api agriprofit-frontend nginx postgresql

# Stop all services
sudo systemctl stop agriprofit-api agriprofit-frontend

# Restart all services
sudo systemctl restart agriprofit-api agriprofit-frontend nginx

# View logs (real-time)
sudo journalctl -u agriprofit-api -f
sudo journalctl -u agriprofit-frontend -f
sudo tail -f /var/log/nginx/access.log

# Check service status
sudo systemctl status agriprofit-api
sudo systemctl status agriprofit-frontend
sudo systemctl status nginx
sudo systemctl status postgresql

# Database backup
sudo -u agriprofit /opt/agriprofit/scripts/backup_db.sh

# Manual data sync
sudo -u agriprofit /opt/agriprofit/scripts/sync_data.sh

# Check disk space
df -h

# Check memory usage
free -h

# Reload Nginx config
sudo nginx -t && sudo systemctl reload nginx
```

---

## Support

For issues or questions:
- Check logs: `/opt/agriprofit/logs/`
- Review this guide
- Contact: [your-support-email]

---

**Deployment Guide Version**: 1.0  
**Last Updated**: February 2026  
**Status**: Production Ready ✅
