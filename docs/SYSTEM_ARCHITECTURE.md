# AgriProfit System Architecture Contract

**Version:** 1.0.0  
**Status:** LOCKED  
**Date:** January 2026  
**Derived From:** Product Contract v1.0

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [System Components](#2-system-components)
3. [Technology Stack](#3-technology-stack)
4. [Data Architecture](#4-data-architecture)
5. [API Architecture](#5-api-architecture)
6. [Authentication & Security](#6-authentication--security)
7. [Infrastructure & Deployment](#7-infrastructure--deployment)
8. [Integration Points](#8-integration-points)
9. [Performance & Scalability](#9-performance--scalability)
10. [Monitoring & Observability](#10-monitoring--observability)
11. [Development Standards](#11-development-standards)
12. [Constraints & Boundaries](#12-constraints--boundaries)

---

## 1. Architecture Overview

### 1.1 Architecture Style

**Pattern:** Modular Monolith

AgriProfit uses a modular monolith architecture, NOT microservices. This decision is based on:

- Project scope (Mini Project)
- Team size constraints
- Deployment simplicity (Docker-based)
- Low-cost cloud compatibility
- Faster development cycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│    ┌─────────────────────┐         ┌─────────────────────┐         │
│    │     Web App         │         │    Mobile App       │         │
│    │    (Next.js)        │         │   (React Native)    │         │
│    │                     │         │                     │         │
│    │  • SSR/SSG Pages    │         │  • iOS App          │         │
│    │  • React Components │         │  • Android App      │         │
│    │  • TailwindCSS      │         │  • Shared Codebase  │         │
│    └──────────┬──────────┘         └──────────┬──────────┘         │
│               │                               │                     │
└───────────────┼───────────────────────────────┼─────────────────────┘
                │                               │
                │         HTTPS/REST            │
                └───────────────┬───────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────┐
│                         API LAYER                                    │
├───────────────────────────────┼─────────────────────────────────────┤
│                               ▼                                      │
│    ┌─────────────────────────────────────────────────────────┐      │
│    │                    FastAPI Backend                       │      │
│    │                   (Single Instance)                      │      │
│    ├─────────────────────────────────────────────────────────┤      │
│    │                                                          │      │
│    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │      │
│    │  │   Auth   │ │  Price   │ │Transport │ │Community │   │      │
│    │  │  Module  │ │  Module  │ │  Module  │ │  Module  │   │      │
│    │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │      │
│    │                                                          │      │
│    │  ┌──────────┐ ┌──────────┐ ┌──────────┐                │      │
│    │  │  Alert   │ │  Notify  │ │  Admin   │                │      │
│    │  │  Module  │ │  Module  │ │  Module  │                │      │
│    │  └──────────┘ └──────────┘ └──────────┘                │      │
│    │                                                          │      │
│    └─────────────────────────────────────────────────────────┘      │
│                               │                                      │
└───────────────────────────────┼──────────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────────┐
│                         DATA LAYER                                    │
├───────────────────────────────┼──────────────────────────────────────┤
│                               ▼                                       │
│    ┌─────────────────────┐         ┌─────────────────────┐           │
│    │     PostgreSQL      │         │       Redis         │           │
│    │   (Primary Store)   │         │   (Cache + OTP)     │           │
│    │                     │         │                     │           │
│    │  • Users            │         │  • OTP Storage      │           │
│    │  • Commodities      │         │  • Session Cache    │           │
│    │  • Prices           │         │  • Rate Limiting    │           │
│    │  • Posts            │         │  • Token Blacklist  │           │
│    │  • Notifications    │         │                     │           │
│    │  • Districts        │         │                     │           │
│    └─────────────────────┘         └─────────────────────┘           │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture Pattern | Modular Monolith | Simplicity, single deployment |
| Backend Framework | FastAPI | Product Contract requirement |
| Primary Database | PostgreSQL | ACID compliance, JSON support |
| Cache Layer | Redis | OTP, sessions, rate limiting |
| Frontend Web | Next.js | Product Contract requirement |
| Frontend Mobile | React Native | Product Contract requirement |
| Containerization | Docker | Product Contract requirement |
| API Style | REST | Simplicity, wide compatibility |

### 1.3 Single Backend Principle

**CRITICAL:** There is ONE backend serving both web and mobile.

```
                    ┌─────────────────┐
                    │   Web App       │──────┐
                    │   (Next.js)     │      │
                    └─────────────────┘      │
                                             │    ┌─────────────────┐
                                             ├───►│   FastAPI       │
                                             │    │   Backend       │
                    ┌─────────────────┐      │    │   (Single)      │
                    │   Mobile App    │──────┘    └─────────────────┘
                    │   (React Native)│
                    └─────────────────┘
```

- No separate backends for web/mobile
- No BFF (Backend for Frontend) pattern
- Same endpoints, same logic, same data

---

## 2. System Components

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                         API ROUTER                               │    │
│  │  /api/v1/auth/* │ /api/v1/users/* │ /api/v1/prices/* │ ...     │    │
│  └───────────────────────────────┬─────────────────────────────────┘    │
│                                  │                                       │
│  ┌───────────────────────────────┼─────────────────────────────────┐    │
│  │                         MIDDLEWARE                               │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │    │
│  │  │  Auth   │ │  CORS   │ │  Rate   │ │ Request │ │  Error  │   │    │
│  │  │Middleware│ │Middleware│ │ Limit  │ │ Logging │ │ Handler │   │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │    │
│  └───────────────────────────────┬─────────────────────────────────┘    │
│                                  │                                       │
│  ┌───────────────────────────────┼─────────────────────────────────┐    │
│  │                    APPLICATION MODULES                           │    │
│  │                                                                  │    │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │    │
│  │  │  AUTH MODULE   │  │  USER MODULE   │  │  PRICE MODULE  │    │    │
│  │  │                │  │                │  │                │    │    │
│  │  │ • OTP Request  │  │ • Get Profile  │  │ • History      │    │    │
│  │  │ • OTP Verify   │  │ • Update       │  │ • Forecast     │    │    │
│  │  │ • Token Refresh│  │   Profile      │  │ • Compare      │    │    │
│  │  │ • Logout       │  │                │  │ • Commodities  │    │    │
│  │  └────────────────┘  └────────────────┘  └────────────────┘    │    │
│  │                                                                  │    │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │    │
│  │  │TRANSPORT MODULE│  │COMMUNITY MODULE│  │  ALERT MODULE  │    │    │
│  │  │                │  │                │  │                │    │    │
│  │  │ • Calculate    │  │ • Create Post  │  │ • Create Alert │    │    │
│  │  │ • Compare      │  │ • List Posts   │  │ • Pin Logic    │    │    │
│  │  │                │  │ • Delete Post  │  │ • Highlight    │    │    │
│  │  └────────────────┘  └────────────────┘  └────────────────┘    │    │
│  │                                                                  │    │
│  │  ┌────────────────┐  ┌────────────────┐                        │    │
│  │  │ NOTIFY MODULE  │  │  ADMIN MODULE  │                        │    │
│  │  │                │  │                │                        │    │
│  │  │ • List         │  │ • Broadcast    │                        │    │
│  │  │ • Mark Read    │  │ • Moderate     │                        │    │
│  │  │ • Create       │  │ • Stats        │                        │    │
│  │  └────────────────┘  └────────────────┘                        │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                  │                                       │
│  ┌───────────────────────────────┼─────────────────────────────────┐    │
│  │                         CORE SERVICES                            │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │    │
│  │  │   OTP   │ │  JWT    │ │District │ │Forecast │ │  Audit  │   │    │
│  │  │ Service │ │ Service │ │ Service │ │ Service │ │ Logger  │   │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │    │
│  └───────────────────────────────┬─────────────────────────────────┘    │
│                                  │                                       │
│  ┌───────────────────────────────┼─────────────────────────────────┐    │
│  │                         DATA ACCESS                              │    │
│  │  ┌─────────────────────┐    ┌─────────────────────┐             │    │
│  │  │   SQLAlchemy ORM    │    │    Redis Client     │             │    │
│  │  │   (PostgreSQL)      │    │    (aioredis)       │             │    │
│  │  └─────────────────────┘    └─────────────────────┘             │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Module Responsibilities

| Module | Responsibilities | Dependencies |
|--------|-----------------|--------------|
| **Auth** | OTP generation, verification, JWT issuance, token refresh, logout | Redis (OTP), PostgreSQL (users) |
| **User** | Profile management, district association | PostgreSQL |
| **Price** | Historical data, forecasting, comparisons | PostgreSQL |
| **Transport** | Cost calculation, multi-district comparison | PostgreSQL (districts) |
| **Community** | Post CRUD, listing with filters | PostgreSQL |
| **Alert** | Alert creation, pin/highlight logic, district-based visibility | PostgreSQL, District Service |
| **Notify** | Notification creation, listing, read status | PostgreSQL |
| **Admin** | Broadcasting, moderation, statistics | All modules |

### 2.3 Core Services

| Service | Purpose |
|---------|---------|
| **OTP Service** | Generate, store, validate OTPs |
| **JWT Service** | Token creation, validation, refresh |
| **District Service** | District lookup, neighbor calculation |
| **Forecast Service** | Simple time-series prediction |
| **Audit Logger** | Action logging for compliance |

---

## 3. Technology Stack

### 3.1 Stack Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        TECHNOLOGY STACK                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  FRONTEND                                                        │
│  ├── Web: Next.js 14+ (App Router)                              │
│  │   ├── React 18+                                              │
│  │   ├── TypeScript                                             │
│  │   ├── TailwindCSS                                            │
│  │   ├── React Query (TanStack Query)                           │
│  │   └── Zustand (State Management)                             │
│  │                                                               │
│  └── Mobile: React Native 0.73+                                 │
│      ├── Expo SDK 50+                                           │
│      ├── TypeScript                                             │
│      ├── React Navigation 6                                     │
│      ├── React Query                                            │
│      └── Zustand                                                │
│                                                                  │
│  BACKEND                                                         │
│  ├── Framework: FastAPI 0.109+                                  │
│  ├── Language: Python 3.11+                                     │
│  ├── ORM: SQLAlchemy 2.0+                                       │
│  ├── Migrations: Alembic                                        │
│  ├── Validation: Pydantic 2.0+                                  │
│  ├── Async: asyncio + asyncpg                                   │
│  └── Testing: pytest + pytest-asyncio                           │
│                                                                  │
│  DATA                                                            │
│  ├── Primary DB: PostgreSQL 15+                                 │
│  ├── Cache: Redis 7+                                            │
│  └── Migrations: Alembic                                        │
│                                                                  │
│  INFRASTRUCTURE                                                  │
│  ├── Containerization: Docker                                   │
│  ├── Orchestration: Docker Compose                              │
│  ├── Reverse Proxy: Nginx (optional)                            │
│  └── Cloud: Any Docker-compatible (Railway, Render, etc.)       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Version Requirements

| Component | Minimum Version | Notes |
|-----------|-----------------|-------|
| Python | 3.11 | Required for FastAPI performance |
| FastAPI | 0.109 | Latest stable |
| PostgreSQL | 15 | JSON support, performance |
| Redis | 7 | Latest stable |
| Node.js | 20 LTS | For Next.js |
| Next.js | 14 | App Router |
| React Native | 0.73 | Latest stable |
| Docker | 24 | BuildKit support |
| Docker Compose | 2.24 | Latest features |

### 3.3 Python Dependencies

```
# Core
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Database
sqlalchemy>=2.0.25
asyncpg>=0.29.0
alembic>=1.13.0

# Cache
redis>=5.0.0

# Auth
python-jose[cryptography]>=3.3.0
passlib>=1.7.4

# Validation
email-validator>=2.1.0
phonenumbers>=8.13.0

# HTTP
httpx>=0.26.0

# Utils
python-multipart>=0.0.6
python-dotenv>=1.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
httpx>=0.26.0
```

---

## 4. Data Architecture

### 4.1 Database Schema

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATABASE SCHEMA                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐       ┌─────────────────┐                          │
│  │     states      │       │    districts    │                          │
│  ├─────────────────┤       ├─────────────────┤                          │
│  │ code (PK)       │◄──────│ state_code (FK) │                          │
│  │ name            │       │ code (PK)       │                          │
│  │ name_ml         │       │ name            │                          │
│  └─────────────────┘       │ name_ml         │                          │
│                            │ latitude        │                          │
│                            │ longitude       │                          │
│                            │ neighbors[]     │                          │
│                            └────────┬────────┘                          │
│                                     │                                    │
│                     ┌───────────────┼───────────────┐                   │
│                     │               │               │                    │
│                     ▼               ▼               ▼                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │      users      │  │  market_prices  │  │district_distances│         │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤         │
│  │ id (PK)         │  │ id (PK)         │  │ from_code (FK)  │         │
│  │ phone           │  │ commodity_id(FK)│  │ to_code (FK)    │         │
│  │ name            │  │ district_code   │  │ distance_km     │         │
│  │ role            │  │ price_date      │  └─────────────────┘         │
│  │ district_code   │  │ price           │                               │
│  │ language        │  │ volume          │                               │
│  │ created_at      │  └─────────────────┘                               │
│  │ updated_at      │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                              │
│           │         ┌─────────────────┐                                 │
│           │         │   commodities   │                                 │
│           │         ├─────────────────┤                                 │
│           │         │ id (PK)         │                                 │
│           │         │ name            │                                 │
│           │         │ name_ml         │                                 │
│           │         │ category        │                                 │
│           │         │ unit            │                                 │
│           │         │ icon_url        │                                 │
│           │         └─────────────────┘                                 │
│           │                                                              │
│           ├────────────────────┬────────────────────┐                   │
│           │                    │                    │                    │
│           ▼                    ▼                    ▼                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │      posts      │  │  notifications  │  │  refresh_tokens │         │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤         │
│  │ id (PK)         │  │ id (PK)         │  │ id (PK)         │         │
│  │ author_id (FK)  │  │ user_id (FK)    │  │ user_id (FK)    │         │
│  │ type            │  │ type            │  │ token_hash      │         │
│  │ title           │  │ title           │  │ expires_at      │         │
│  │ content         │  │ body            │  │ revoked         │         │
│  │ district_code   │  │ reference_type  │  │ created_at      │         │
│  │ is_broadcast    │  │ reference_id    │  └─────────────────┘         │
│  │ broadcast_target│  │ read            │                               │
│  │ created_at      │  │ read_at         │                               │
│  │ deleted_at      │  │ created_at      │                               │
│  └─────────────────┘  └─────────────────┘                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Table Definitions

#### 4.2.1 Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'farmer',
    district_code VARCHAR(10) REFERENCES districts(code),
    preferred_language VARCHAR(5) DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_role CHECK (role IN ('farmer', 'admin')),
    CONSTRAINT valid_language CHECK (preferred_language IN ('en', 'ml'))
);

CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_district ON users(district_code);
```

#### 4.2.2 Districts Table

```sql
CREATE TABLE states (
    code VARCHAR(5) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_ml VARCHAR(100)
);

CREATE TABLE districts (
    code VARCHAR(10) PRIMARY KEY,
    state_code VARCHAR(5) NOT NULL REFERENCES states(code),
    name VARCHAR(100) NOT NULL,
    name_ml VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    neighbors TEXT[] DEFAULT '{}',
    
    CONSTRAINT valid_code_format CHECK (code ~ '^[A-Z]{2}-[A-Z]{3}$')
);

CREATE INDEX idx_districts_state ON districts(state_code);
```

#### 4.2.3 Commodities & Prices Tables

```sql
CREATE TABLE commodities (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_ml VARCHAR(100),
    category VARCHAR(50) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    icon_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE market_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commodity_id VARCHAR(50) NOT NULL REFERENCES commodities(id),
    district_code VARCHAR(10) NOT NULL REFERENCES districts(code),
    price_date DATE NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    volume INTEGER,
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_price_entry UNIQUE (commodity_id, district_code, price_date)
);

CREATE INDEX idx_prices_commodity ON market_prices(commodity_id);
CREATE INDEX idx_prices_district ON market_prices(district_code);
CREATE INDEX idx_prices_date ON market_prices(price_date DESC);
CREATE INDEX idx_prices_lookup ON market_prices(commodity_id, district_code, price_date DESC);
```

#### 4.2.4 Posts Table

```sql
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(20) NOT NULL DEFAULT 'post',
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    district_code VARCHAR(10) NOT NULL REFERENCES districts(code),
    is_broadcast BOOLEAN DEFAULT FALSE,
    broadcast_target VARCHAR(50),
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES users(id),
    deletion_reason TEXT,
    
    CONSTRAINT valid_post_type CHECK (type IN ('post', 'alert'))
);

CREATE INDEX idx_posts_author ON posts(author_id);
CREATE INDEX idx_posts_district ON posts(district_code);
CREATE INDEX idx_posts_type ON posts(type);
CREATE INDEX idx_posts_created ON posts(created_at DESC);
CREATE INDEX idx_posts_active ON posts(created_at DESC) WHERE deleted_at IS NULL;
```

#### 4.2.5 Notifications Table

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    reference_type VARCHAR(50),
    reference_id UUID,
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_notification_type CHECK (type IN ('alert_nearby', 'system_broadcast'))
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, created_at DESC) WHERE read = FALSE;
```

#### 4.2.6 Refresh Tokens Table

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_token UNIQUE (token_hash)
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash) WHERE revoked = FALSE;
```

#### 4.2.7 District Distances Table

```sql
CREATE TABLE district_distances (
    from_district_code VARCHAR(10) NOT NULL REFERENCES districts(code),
    to_district_code VARCHAR(10) NOT NULL REFERENCES districts(code),
    distance_km INTEGER NOT NULL,
    
    PRIMARY KEY (from_district_code, to_district_code)
);
```

#### 4.2.8 Audit Log Table

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
```

### 4.3 Redis Data Structures

```
┌─────────────────────────────────────────────────────────────────┐
│                       REDIS SCHEMA                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  OTP Storage                                                     │
│  ────────────                                                    │
│  Key:    otp:{request_id}                                       │
│  Type:   Hash                                                    │
│  TTL:    300 seconds (5 minutes)                                │
│  Fields:                                                         │
│    - phone: "9876543210"                                        │
│    - otp: "123456"                                              │
│    - attempts: 0                                                │
│    - created_at: "2026-01-19T10:30:00Z"                        │
│                                                                  │
│  Rate Limiting (OTP)                                            │
│  ────────────────────                                           │
│  Key:    rate:otp:{phone}                                       │
│  Type:   String (counter)                                       │
│  TTL:    60 seconds                                             │
│                                                                  │
│  Rate Limiting (API)                                            │
│  ────────────────────                                           │
│  Key:    rate:api:{user_id}:{endpoint_category}                │
│  Type:   String (counter)                                       │
│  TTL:    60 seconds                                             │
│                                                                  │
│  Token Blacklist                                                │
│  ────────────────                                               │
│  Key:    blacklist:{token_jti}                                  │
│  Type:   String ("1")                                           │
│  TTL:    Remaining token lifetime                               │
│                                                                  │
│  Session Cache (Optional)                                       │
│  ────────────────────────                                       │
│  Key:    session:{user_id}                                      │
│  Type:   Hash                                                   │
│  TTL:    86400 seconds (24 hours)                              │
│  Fields:                                                         │
│    - role: "farmer"                                             │
│    - district_code: "KL-EKM"                                   │
│    - name: "Rajesh Kumar"                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. API Architecture

### 5.1 API Structure

```
/api/v1/
├── auth/
│   ├── POST   /otp/request
│   ├── POST   /otp/verify
│   ├── POST   /token/refresh
│   └── POST   /logout
│
├── users/
│   ├── GET    /me
│   └── PATCH  /me
│
├── commodities/
│   └── GET    /
│
├── prices/
│   ├── GET    /history
│   ├── GET    /forecast
│   └── GET    /compare
│
├── transport/
│   ├── POST   /calculate
│   └── POST   /compare
│
├── posts/
│   ├── GET    /
│   ├── GET    /{post_id}
│   ├── POST   /
│   └── DELETE /{post_id}
│
├── notifications/
│   ├── GET    /
│   ├── POST   /{notification_id}/read
│   └── POST   /read-all
│
└── admin/
    ├── POST   /alerts/broadcast
    ├── DELETE /posts/{post_id}
    └── GET    /stats
```

### 5.2 Request/Response Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │────►│Middleware│────►│  Router  │────►│  Handler │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                                  │
                      ▼                                  ▼
               ┌──────────┐                       ┌──────────┐
               │   Auth   │                       │ Service  │
               │   Check  │                       │  Layer   │
               └──────────┘                       └──────────┘
                      │                                  │
                      ▼                                  ▼
               ┌──────────┐                       ┌──────────┐
               │   Rate   │                       │   Data   │
               │  Limit   │                       │  Access  │
               └──────────┘                       └──────────┘
                                                       │
                                                       ▼
                                                 ┌──────────┐
                                                 │ Database │
                                                 └──────────┘
```

### 5.3 Middleware Stack

```python
# Order of middleware execution (top to bottom)
app = FastAPI()

# 1. CORS
app.add_middleware(CORSMiddleware, ...)

# 2. Request ID
app.add_middleware(RequestIDMiddleware)

# 3. Request Logging
app.add_middleware(RequestLoggingMiddleware)

# 4. Rate Limiting
app.add_middleware(RateLimitMiddleware)

# 5. Error Handling (via exception handlers)
@app.exception_handler(Exception)
async def global_exception_handler(request, exc): ...
```

---

## 6. Authentication & Security

### 6.1 Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. OTP Request                                                  │
│  ───────────────                                                │
│  Client ──► POST /auth/otp/request {phone}                      │
│         ◄── {request_id, expires_at}                            │
│                                                                  │
│  Backend:                                                        │
│    • Validate phone format                                      │
│    • Check rate limit (Redis)                                   │
│    • Generate 6-digit OTP                                       │
│    • Store in Redis with 5-min TTL                             │
│    • Log OTP to console (dev) / send via SMS gateway (prod)    │
│                                                                  │
│  2. OTP Verify                                                  │
│  ─────────────                                                  │
│  Client ──► POST /auth/otp/verify {request_id, otp}            │
│         ◄── {access_token, refresh_token, user}                 │
│                                                                  │
│  Backend:                                                        │
│    • Retrieve OTP from Redis                                    │
│    • Validate OTP (max 3 attempts)                             │
│    • Create user if new (auto-registration)                    │
│    • Generate JWT access token (24h)                           │
│    • Generate refresh token (30d)                              │
│    • Store refresh token hash in PostgreSQL                    │
│    • Delete OTP from Redis                                     │
│                                                                  │
│  3. Token Refresh                                               │
│  ────────────────                                               │
│  Client ──► POST /auth/token/refresh {refresh_token}           │
│         ◄── {access_token}                                      │
│                                                                  │
│  Backend:                                                        │
│    • Validate refresh token signature                          │
│    • Check token not revoked in database                       │
│    • Generate new access token                                 │
│                                                                  │
│  4. Logout                                                      │
│  ─────────                                                      │
│  Client ──► POST /auth/logout (with Authorization header)      │
│         ◄── {message: "Logged out"}                            │
│                                                                  │
│  Backend:                                                        │
│    • Add access token JTI to blacklist (Redis)                │
│    • Revoke refresh token in database                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 JWT Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                      JWT ACCESS TOKEN                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Header:                                                         │
│  {                                                               │
│    "alg": "HS256",                                              │
│    "typ": "JWT"                                                 │
│  }                                                               │
│                                                                  │
│  Payload:                                                        │
│  {                                                               │
│    "sub": "usr_a1b2c3d4e5f6",      // User ID                  │
│    "role": "farmer",                // Role                     │
│    "district_code": "KL-EKM",       // District (nullable)     │
│    "jti": "unique-token-id",        // Token ID (for blacklist)│
│    "iat": 1738339200,               // Issued at               │
│    "exp": 1738425600                // Expires at (24h)        │
│  }                                                               │
│                                                                  │
│  Signature:                                                      │
│  HMACSHA256(base64UrlEncode(header) + "." +                    │
│             base64UrlEncode(payload), SECRET_KEY)               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Security Measures

| Measure | Implementation |
|---------|----------------|
| **Password Storage** | N/A (OTP-based auth) |
| **OTP Security** | 6 digits, 5-min expiry, 3 attempts max |
| **Token Security** | HS256 signing, short-lived access tokens |
| **HTTPS** | Required in production |
| **CORS** | Whitelist specific origins |
| **Rate Limiting** | Redis-based, per-endpoint limits |
| **Input Validation** | Pydantic models for all inputs |
| **SQL Injection** | SQLAlchemy ORM (parameterized queries) |
| **XSS Protection** | JSON-only API, no HTML rendering |
| **Audit Logging** | All sensitive actions logged |

### 6.4 Role-Based Access Control

```
┌─────────────────────────────────────────────────────────────────┐
│                    RBAC IMPLEMENTATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Roles: farmer, admin                                           │
│                                                                  │
│  Endpoint Protection:                                           │
│                                                                  │
│  @router.get("/prices/history")                                 │
│  async def get_history(current_user: User = Depends(get_user)):│
│      # Any authenticated user                                   │
│      ...                                                        │
│                                                                  │
│  @router.post("/admin/alerts/broadcast")                        │
│  async def broadcast(current_user: User = Depends(require_admin)):│
│      # Admin only                                               │
│      ...                                                        │
│                                                                  │
│  Dependency Functions:                                          │
│                                                                  │
│  async def get_current_user(token: str) -> User:               │
│      # Validates token, returns user                           │
│      # Raises 401 if invalid                                   │
│                                                                  │
│  async def require_admin(user: User = Depends(get_current_user)):│
│      if user.role != "admin":                                  │
│          raise HTTPException(403, "Admin access required")     │
│      return user                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Infrastructure & Deployment

### 7.1 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                      ┌─────────────┐                            │
│                      │   Internet  │                            │
│                      └──────┬──────┘                            │
│                             │                                    │
│                             ▼                                    │
│                      ┌─────────────┐                            │
│                      │   Nginx     │                            │
│                      │  (Reverse   │                            │
│                      │   Proxy)    │                            │
│                      └──────┬──────┘                            │
│                             │                                    │
│           ┌─────────────────┼─────────────────┐                 │
│           │                 │                 │                  │
│           ▼                 ▼                 ▼                  │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│    │  Next.js    │  │   FastAPI   │  │   Static    │           │
│    │   (Web)     │  │  (Backend)  │  │   Assets    │           │
│    │  :3000      │  │   :8000     │  │             │           │
│    └─────────────┘  └──────┬──────┘  └─────────────┘           │
│                            │                                     │
│              ┌─────────────┴─────────────┐                      │
│              │                           │                       │
│              ▼                           ▼                       │
│       ┌─────────────┐           ┌─────────────┐                 │
│       │ PostgreSQL  │           │    Redis    │                 │
│       │   :5432     │           │    :6379    │                 │
│       └─────────────┘           └─────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Docker Configuration

#### docker-compose.yml

```yaml
version: "3.8"

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: agriprofit-db
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: agriprofit-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: agriprofit-backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - ENVIRONMENT=${ENVIRONMENT}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Next.js Web App
  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    container_name: agriprofit-web
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api/v1
    ports:
      - "3000:3000"
    depends_on:
      - backend

  # Nginx Reverse Proxy (Production)
  nginx:
    image: nginx:alpine
    container_name: agriprofit-nginx
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
      - web

volumes:
  postgres_data:
  redis_data:
```

#### Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
```

#### Web Dockerfile

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

CMD ["node", "server.js"]
```

### 7.3 Environment Variables

```bash
# .env.example

# Database
DB_USER=agriprofit
DB_PASSWORD=secure_password_here
DB_NAME=agriprofit
DATABASE_URL=postgresql+asyncpg://agriprofit:password@localhost:5432/agriprofit

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=your-256-bit-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8081

# Rate Limiting
RATE_LIMIT_OTP=10/minute
RATE_LIMIT_READ=300/minute
RATE_LIMIT_WRITE=60/minute
```

### 7.4 Cloud Deployment Options

| Provider | Service | Cost Tier | Notes |
|----------|---------|-----------|-------|
| **Railway** | Full stack | Free/Hobby | Easiest deployment |
| **Render** | Full stack | Free tier | Good free tier |
| **Fly.io** | Backend + DB | Free tier | Global edge |
| **Supabase** | PostgreSQL | Free tier | Managed Postgres |
| **Upstash** | Redis | Free tier | Serverless Redis |
| **Vercel** | Next.js | Free tier | Best for Next.js |

**Recommended Stack (Low-Cost):**
- Backend: Railway or Render
- Database: Supabase (PostgreSQL)
- Cache: Upstash (Redis)
- Web: Vercel
- Mobile: Expo EAS (build service)

---

## 8. Integration Points

### 8.1 External Integrations

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTEGRATION POINTS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  REQUIRED (v1):                                                  │
│  ──────────────                                                 │
│  None - All data is seeded/managed internally                   │
│                                                                  │
│  OPTIONAL (Future):                                             │
│  ─────────────────                                              │
│  • SMS Gateway (for production OTP delivery)                   │
│    - Twilio, MSG91, or similar                                 │
│    - Abstracted behind OTPService interface                    │
│                                                                  │
│  • Price Data API (for real market prices)                     │
│    - Agmarknet API                                             │
│    - Data.gov.in APIs                                          │
│    - Abstracted behind PriceDataService interface              │
│                                                                  │
│  NOT INTEGRATED (Out of Scope):                                │
│  ──────────────────────────────                                │
│  ✗ Payment gateways                                            │
│  ✗ Email services                                              │
│  ✗ Push notification services (FCM/APNS)                       │
│  ✗ Maps/routing APIs                                           │
│  ✗ Weather APIs                                                │
│  ✗ ML/AI services                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Internal Service Communication

All communication is **synchronous** within the monolith:

```python
# Example: Creating an alert triggers notifications

class AlertService:
    def __init__(self, db: Session, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service
    
    async def create_alert(self, author: User, data: AlertCreate) -> Post:
        # 1. Create the alert post
        alert = await self._create_post(author, data)
        
        # 2. Determine affected users (same + neighboring districts)
        affected_users = await self._get_affected_users(author.district_code)
        
        # 3. Create notifications (synchronous, same transaction)
        await self.notification_service.create_bulk(
            users=affected_users,
            notification_type="alert_nearby",
            reference=alert
        )
        
        return alert
```

---

## 9. Performance & Scalability

### 9.1 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time (p50) | < 100ms | Excluding network |
| API Response Time (p95) | < 500ms | Excluding network |
| API Response Time (p99) | < 1000ms | Excluding network |
| Concurrent Users | 1000+ | Theoretical capacity |
| Database Queries per Request | ≤ 5 | Average |
| Uptime | 99% | Monthly |

### 9.2 Scalability Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCALABILITY APPROACH                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CURRENT (v1):                                                   │
│  ─────────────                                                  │
│  Single instance of each component                              │
│  Vertical scaling (bigger instance) if needed                   │
│                                                                  │
│  FUTURE (if needed):                                            │
│  ────────────────                                               │
│  1. Horizontal Backend Scaling                                  │
│     • Stateless backend allows multiple instances              │
│     • Load balancer in front                                   │
│     • Redis for shared state (sessions, rate limits)          │
│                                                                  │
│  2. Database Scaling                                            │
│     • Read replicas for query distribution                     │
│     • Connection pooling (PgBouncer)                          │
│     • Query optimization & indexing                           │
│                                                                  │
│  3. Caching Layer                                               │
│     • Redis caching for frequent queries                       │
│     • Cache commodity prices (refresh every hour)             │
│     • Cache district data (static)                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 Optimization Techniques

| Area | Technique |
|------|-----------|
| **Database** | Proper indexing, query optimization, connection pooling |
| **API** | Pagination, field selection, response compression |
| **Caching** | Redis for hot data, HTTP cache headers |
| **Frontend** | Code splitting, lazy loading, image optimization |

---

## 10. Monitoring & Observability

### 10.1 Logging Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                      LOGGING STRATEGY                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Log Levels:                                                     │
│  ───────────                                                    │
│  DEBUG   - Detailed debugging (dev only)                        │
│  INFO    - Request/response logging, business events           │
│  WARNING - Recoverable issues, deprecations                    │
│  ERROR   - Failures requiring attention                        │
│  CRITICAL- System failures                                     │
│                                                                  │
│  Log Format (JSON):                                             │
│  ─────────────────                                              │
│  {                                                               │
│    "timestamp": "2026-01-19T10:30:00Z",                        │
│    "level": "INFO",                                             │
│    "request_id": "req_abc123",                                 │
│    "user_id": "usr_xyz789",                                    │
│    "action": "POST /api/v1/posts",                             │
│    "duration_ms": 45,                                          │
│    "status_code": 201,                                         │
│    "message": "Post created successfully"                      │
│  }                                                               │
│                                                                  │
│  Log Storage:                                                    │
│  ────────────                                                   │
│  • Development: Console output                                  │
│  • Production: File + optional log aggregator                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Health Checks

```python
# Health check endpoints

@app.get("/health")
async def health_check():
    """Basic liveness check"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/health/ready")
async def readiness_check(db: Session, redis: Redis):
    """Readiness check with dependencies"""
    checks = {
        "database": await check_database(db),
        "redis": await check_redis(redis)
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow()
    }
```

### 10.3 Metrics (Optional)

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | Request latency |
| `db_query_duration_seconds` | Histogram | Database query time |
| `active_users` | Gauge | Currently active users |
| `otp_requests_total` | Counter | OTP requests sent |

---

## 11. Development Standards

### 11.1 Project Structure

```
agriprofit/
├── backend/
│   ├── alembic/                 # Database migrations
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings
│   │   ├── database.py          # DB connection
│   │   │
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── post.py
│   │   │   ├── commodity.py
│   │   │   └── ...
│   │   │
│   │   ├── schemas/             # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   └── ...
│   │   │
│   │   ├── api/                 # API routes
│   │   │   ├── __init__.py
│   │   │   ├── deps.py          # Dependencies
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py    # Main router
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── prices.py
│   │   │       └── ...
│   │   │
│   │   ├── services/            # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── otp_service.py
│   │   │   ├── price_service.py
│   │   │   └── ...
│   │   │
│   │   ├── core/                # Core utilities
│   │   │   ├── __init__.py
│   │   │   ├── security.py      # JWT, hashing
│   │   │   ├── exceptions.py    # Custom exceptions
│   │   │   └── logging.py
│   │   │
│   │   └── middleware/          # Custom middleware
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       └── rate_limit.py
│   │
│   ├── tests/                   # Test files
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   └── ...
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── alembic.ini
│
├── web/                         # Next.js web app
│   ├── src/
│   │   ├── app/                 # App router pages
│   │   ├── components/
│   │   ├── lib/                 # Utilities
│   │   ├── hooks/               # Custom hooks
│   │   └── services/            # API clients
│   ├── Dockerfile
│   └── package.json
│
├── mobile/                      # React Native app
│   ├── src/
│   │   ├── screens/
│   │   ├── components/
│   │   ├── navigation/
│   │   ├── hooks/
│   │   └── services/
│   ├── app.json
│   └── package.json
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── README.md
```

### 11.2 Coding Standards

| Language | Standard | Tooling |
|----------|----------|---------|
| Python | PEP 8 | Black, Ruff, mypy |
| TypeScript | ESLint + Prettier | eslint, prettier |
| SQL | Lowercase keywords | SQLFluff (optional) |

### 11.3 Git Workflow

```
main (production)
  │
  └── develop (integration)
        │
        ├── feature/auth-module
        ├── feature/price-api
        ├── bugfix/otp-validation
        └── ...
```

**Commit Message Format:**
```
<type>(<scope>): <description>

[optional body]

Types: feat, fix, docs, style, refactor, test, chore
Scope: auth, prices, posts, admin, etc.
```

---

## 12. Constraints & Boundaries

### 12.1 What This Architecture Supports

✅ Phone + OTP authentication  
✅ Two user roles (farmer, admin)  
✅ Historical price analytics  
✅ Simple time-series forecasting  
✅ Transport cost calculation  
✅ Community posts and alerts  
✅ District-based alert pinning  
✅ In-app notifications  
✅ Admin broadcasting and moderation  
✅ Docker-based deployment  
✅ 1000+ concurrent users (theoretical)  

### 12.2 What This Architecture Does NOT Support

❌ Email/SMS notifications (out of scope)  
❌ Real-time features (WebSockets)  
❌ Offline-first mobile mode  
❌ Payment processing  
❌ Advanced ML/AI models  
❌ Multi-tenancy  
❌ Microservices decomposition  
❌ GraphQL API  
❌ Blockchain/Web3  

### 12.3 Architectural Boundaries

| Boundary | Rationale |
|----------|-----------|
| Single backend | Product contract requirement |
| REST only | Simplicity, wide compatibility |
| No real-time | Scope limitation, complexity |
| Modular monolith | Project size, team constraints |
| PostgreSQL + Redis only | No need for additional data stores |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-19 | Architecture Team | Initial release |

---

## 🔒 STATUS: LOCKED

This architecture contract is now **LOCKED**.

- ❌ No additional components
- ❌ No technology changes
- ❌ No scope expansion
- ✅ Only implementation and bug fixes

Any architectural changes require formal review and version increment.

---

*This document serves as the authoritative architecture specification for AgriProfit. All implementation must conform to this specification.*