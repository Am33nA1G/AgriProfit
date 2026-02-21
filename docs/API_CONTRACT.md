# AgriProfit API Contract

**Version:** 1.0.0  
**Status:** Final  
**Last Updated:** January 2026  
**Base URL:** `https://api.agriprofit.in/api/v1`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Global Conventions](#3-global-conventions)
4. [Error Handling](#4-error-handling)
5. [API Endpoints](#5-api-endpoints)
6. [Data Models](#6-data-models)
7. [Appendix](#7-appendix)

---

## 1. Overview

### 1.1 Product Description

AgriProfit is a cloud-based SaaS platform for farmers in India. It provides commodity price analytics, price forecasting, transport cost comparison, and community features.

### 1.2 Architecture

| Component | Technology |
|-----------|------------|
| Architecture | Modular Monolith |
| Backend Framework | FastAPI |
| Database | PostgreSQL |
| Cache | Redis |
| Deployment | Docker |
| API Style | REST |

### 1.3 Supported Clients

- Web Application
- Mobile Application (iOS/Android)

### 1.4 User Roles

| Role | Description |
|------|-------------|
| `farmer` | Primary user. Can access all farmer-facing features. |
| `admin` | Administrative user. Can moderate content and broadcast alerts. |

### 1.5 Supported Languages

| Code | Language |
|------|----------|
| `en` | English |
| `ml` | Malayalam |

---

## 2. Authentication

### 2.1 Authentication Flow

```
┌─────────┐          ┌─────────┐
│  Client │          │   API   │
└────┬────┘          └────┬────┘
     │ POST /auth/otp/request
     │ {phone}
     │───────────────────>│
     │    200 OK          │
     │    {request_id}    │
     │<───────────────────│
     │                    │
     │ POST /auth/otp/verify
     │ {request_id, otp}  │
     │───────────────────>│
     │    200 OK          │
     │    {access_token,  │
     │     refresh_token} │
     │<───────────────────│
```

### 2.2 Token Specification

| Token Type | Lifetime | Usage |
|------------|----------|-------|
| Access Token | 24 hours | API authentication |
| Refresh Token | 30 days | Obtain new access token |

### 2.3 Authorization Header

```
Authorization: Bearer <access_token>
```

### 2.4 JWT Payload Structure

```json
{
  "sub": "user_uuid",
  "role": "farmer|admin",
  "district_code": "KL-EKM",
  "iat": 1738339200,
  "exp": 1738425600
}
```

---

## 3. Global Conventions

### 3.1 Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Conditional | Bearer token (required for protected endpoints) |
| `Content-Type` | Yes | Must be `application/json` |
| `Accept-Language` | No | `en` or `ml`. Default: `en` |
| `X-Client-Version` | No | Client app version for compatibility tracking |
| `X-Platform` | No | `web`, `ios`, `android` |

### 3.2 Response Headers

| Header | Description |
|--------|-------------|
| `X-Request-Id` | Unique request identifier for debugging |
| `X-RateLimit-Limit` | Maximum requests per window |
| `X-RateLimit-Remaining` | Remaining requests in current window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |

### 3.3 Pagination

All list endpoints use cursor-based pagination.

**Query Parameters:**

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | integer | 20 | 100 | Items per page |
| `cursor` | string | null | - | Opaque cursor for next page |

**Response Structure:**

```json
{
  "data": [],
  "pagination": {
    "limit": 20,
    "has_more": true,
    "next_cursor": "eyJpZCI6MTAwfQ=="
  }
}
```

### 3.4 Timestamps

All timestamps are in ISO 8601 format with UTC timezone: `2026-01-19T10:30:00Z`

### 3.5 Rate Limits

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Authentication | 10 requests | per minute per phone |
| Read Operations | 300 requests | per minute per user |
| Write Operations | 60 requests | per minute per user |
| Admin Operations | 120 requests | per minute per admin |

---

## 4. Error Handling

### 4.1 Global Error Schema

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message in requested language",
    "details": {}
  },
  "request_id": "req_abc123xyz"
}
```

### 4.2 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `INVALID_OTP` | 400 | OTP is incorrect or expired |
| `OTP_EXPIRED` | 400 | OTP has expired |
| `OTP_RATE_LIMITED` | 429 | Too many OTP requests |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `TOKEN_EXPIRED` | 401 | Access token has expired |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### 4.3 Validation Error Details

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": {
      "fields": [
        {"field": "phone", "message": "Phone number must be 10 digits"}
      ]
    }
  },
  "request_id": "req_abc123xyz"
}
```

---

## 5. API Endpoints

### 5.1 Authentication APIs

#### 5.1.1 Request OTP

**`POST /auth/otp/request`**

**Auth:** None

**Request:**
```json
{
  "phone": "9876543210"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `phone` | string | Yes | 10 digits, numeric only |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "request_id": "otp_req_a1b2c3d4e5f6",
    "expires_at": "2026-01-19T10:35:00Z",
    "retry_after_seconds": 60
  }
}
```

**Errors:** `VALIDATION_ERROR` (400), `OTP_RATE_LIMITED` (429)

---

#### 5.1.2 Verify OTP

**`POST /auth/otp/verify`**

**Auth:** None

**Request:**
```json
{
  "request_id": "otp_req_a1b2c3d4e5f6",
  "otp": "123456"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `request_id` | string | Yes | Non-empty |
| `otp` | string | Yes | 6 digits |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 86400,
    "user": {
      "id": "usr_a1b2c3d4e5f6",
      "phone": "9876543210",
      "role": "farmer",
      "is_new_user": true,
      "profile_complete": false
    }
  }
}
```

**Errors:** `VALIDATION_ERROR` (400), `INVALID_OTP` (400), `OTP_EXPIRED` (400), `NOT_FOUND` (404)

---

#### 5.1.3 Refresh Token

**`POST /auth/token/refresh`**

**Auth:** None

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 86400
  }
}
```

**Errors:** `UNAUTHORIZED` (401), `TOKEN_EXPIRED` (401)

---

#### 5.1.4 Logout

**`POST /auth/logout`**

**Auth:** Required

**Request:** None

**Response (200):**
```json
{
  "success": true,
  "data": {
    "message": "Logged out successfully"
  }
}
```

**Errors:** `UNAUTHORIZED` (401)

---

### 5.2 User APIs

#### 5.2.1 Get Current User Profile

**`GET /users/me`**

**Auth:** Required

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": "usr_a1b2c3d4e5f6",
    "phone": "9876543210",
    "role": "farmer",
    "name": "Rajesh Kumar",
    "district_code": "KL-EKM",
    "district_name": "Ernakulam",
    "state_code": "KL",
    "state_name": "Kerala",
    "preferred_language": "ml",
    "profile_complete": true,
    "created_at": "2026-01-15T08:30:00Z",
    "updated_at": "2026-01-18T14:20:00Z"
  }
}
```

**Errors:** `UNAUTHORIZED` (401)

---

#### 5.2.2 Update Current User Profile

**`PATCH /users/me`**

**Auth:** Required

**Request:**
```json
{
  "name": "Rajesh Kumar",
  "district_code": "KL-EKM",
  "preferred_language": "ml"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `name` | string | No | 2-100 characters |
| `district_code` | string | No | Valid district code |
| `preferred_language` | string | No | `en` or `ml` |

**Response (200):** Same as GET /users/me

**Errors:** `VALIDATION_ERROR` (400), `UNAUTHORIZED` (401)

---

### 5.3 Price Analytics APIs

#### 5.3.1 List Commodities

**`GET /commodities`**

**Auth:** Required

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `search` | string | No | Search by name |
| `category` | string | No | Filter by category |
| `limit` | integer | No | Default: 50, Max: 100 |
| `cursor` | string | No | Pagination cursor |

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "cmd_rice_001",
      "name": "Rice (Paddy)",
      "name_ml": "അരി (നെല്ല്)",
      "category": "cereals",
      "unit": "quintal",
      "icon_url": "https://cdn.agriprofit.in/icons/rice.png"
    }
  ],
  "pagination": {
    "limit": 50,
    "has_more": false,
    "next_cursor": null
  }
}
```

---

#### 5.3.2 Get Historical Prices

**`GET /prices/history`**

**Auth:** Required

**Query Parameters:**

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `commodity_id` | string | Yes | Valid commodity ID |
| `district_code` | string | Yes | Valid district code |
| `period` | string | No | `7d`, `30d`, `90d`, `180d`, `1y` (default: `30d`) |
| `granularity` | string | No | `daily`, `weekly`, `monthly` (default: `daily`) |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "commodity": {
      "id": "cmd_rice_001",
      "name": "Rice (Paddy)",
      "unit": "quintal"
    },
    "district": {
      "code": "KL-EKM",
      "name": "Ernakulam"
    },
    "period": {
      "from": "2025-12-20",
      "to": "2026-01-19",
      "granularity": "daily"
    },
    "summary": {
      "current_price": 2850.00,
      "min_price": 2720.00,
      "max_price": 2950.00,
      "avg_price": 2815.50,
      "price_change": 80.00,
      "price_change_percent": 2.89
    },
    "prices": [
      {"date": "2026-01-19", "price": 2850.00, "volume": 450},
      {"date": "2026-01-18", "price": 2830.00, "volume": 380}
    ]
  }
}
```

**Errors:** `VALIDATION_ERROR` (400), `UNAUTHORIZED` (401), `NOT_FOUND` (404)

---

#### 5.3.3 Get Price Forecast

**`GET /prices/forecast`**

**Auth:** Required

**Query Parameters:**

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `commodity_id` | string | Yes | Valid commodity ID |
| `district_code` | string | Yes | Valid district code |
| `horizon` | string | No | `7d`, `14d`, `30d` (default: `7d`) |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "commodity": {
      "id": "cmd_rice_001",
      "name": "Rice (Paddy)",
      "unit": "quintal"
    },
    "district": {
      "code": "KL-EKM",
      "name": "Ernakulam"
    },
    "current_price": 2850.00,
    "forecast": {
      "horizon": "7d",
      "generated_at": "2026-01-19T06:00:00Z",
      "predictions": [
        {
          "date": "2026-01-20",
          "predicted_price": 2860.00,
          "lower_bound": 2800.00,
          "upper_bound": 2920.00
        }
      ],
      "trend": "stable",
      "confidence_level": "medium"
    },
    "disclaimer": {
      "en": "This forecast is based on historical data analysis and is provided for informational purposes only. Actual prices may vary significantly. Do not make financial decisions based solely on this forecast.",
      "ml": "ഈ പ്രവചനം ചരിത്രപരമായ ഡാറ്റാ വിശകലനത്തെ അടിസ്ഥാനമാക്കിയുള്ളതാണ്. യഥാർത്ഥ വിലകൾ ഗണ്യമായി വ്യത്യാസപ്പെടാം."
    }
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `forecast.trend` | string | `rising`, `falling`, `stable` |
| `forecast.confidence_level` | string | `low`, `medium`, `high` |
| `disclaimer` | object | **Mandatory** disclaimers in both languages |

**Errors:** `VALIDATION_ERROR` (400), `UNAUTHORIZED` (401), `NOT_FOUND` (404)

---

#### 5.3.4 Compare Prices Across Districts

**`GET /prices/compare`**

**Auth:** Required

**Query Parameters:**

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `commodity_id` | string | Yes | Valid commodity ID |
| `district_codes` | string | No | Comma-separated, max 10 (default: user's district + neighbors) |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "commodity": {
      "id": "cmd_rice_001",
      "name": "Rice (Paddy)",
      "unit": "quintal"
    },
    "as_of": "2026-01-19",
    "comparisons": [
      {
        "district": {"code": "KL-TVM", "name": "Thiruvananthapuram"},
        "current_price": 2920.00,
        "price_change_7d": 45.00,
        "price_change_percent_7d": 1.56,
        "rank": 1
      }
    ],
    "best_price_district": {
      "code": "KL-TVM",
      "name": "Thiruvananthapuram",
      "price": 2920.00
    }
  }
}
```

---

### 5.4 Transport APIs

#### 5.4.1 Calculate Transport Cost

**`POST /transport/calculate`**

**Auth:** Required

**Request:**
```json
{
  "from_district_code": "KL-EKM",
  "to_district_code": "KL-TVM",
  "quantity": 50
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `from_district_code` | string | Yes | Valid district code |
| `to_district_code` | string | Yes | Valid district code |
| `quantity` | number | Yes | > 0 (in quintals) |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "from_district": {"code": "KL-EKM", "name": "Ernakulam"},
    "to_district": {"code": "KL-TVM", "name": "Thiruvananthapuram"},
    "distance_km": 220,
    "quantity_quintals": 50,
    "calculation": {
      "rate_per_km": 15.00,
      "base_cost": 3300.00,
      "loading_charges": 500.00,
      "unloading_charges": 500.00,
      "total_estimated_cost": 4300.00,
      "cost_per_quintal": 86.00
    },
    "disclaimer": {
      "en": "This is an estimated cost based on average rates. Actual costs may vary.",
      "ml": "ശരാശരി നിരക്കുകളെ അടിസ്ഥാനമാക്കിയുള്ള കണക്കാക്കിയ ചെലവാണിത്."
    }
  }
}
```

**Formula:** `estimated_cost = distance_km × rate_per_km + loading + unloading`

**Errors:** `VALIDATION_ERROR` (400), `UNAUTHORIZED` (401), `NOT_FOUND` (404)

---

#### 5.4.2 Compare Transport to Multiple Districts

**`POST /transport/compare`**

**Auth:** Required

**Request:**
```json
{
  "commodity_id": "cmd_rice_001",
  "from_district_code": "KL-EKM",
  "to_district_codes": ["KL-TVM", "KL-KTM", "KL-TSR"],
  "quantity": 50
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `commodity_id` | string | Yes | Valid commodity ID |
| `from_district_code` | string | Yes | Valid district code |
| `to_district_codes` | array | Yes | Max 10 valid codes |
| `quantity` | number | Yes | > 0 |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "commodity": {"id": "cmd_rice_001", "name": "Rice (Paddy)", "unit": "quintal"},
    "from_district": {"code": "KL-EKM", "name": "Ernakulam"},
    "quantity_quintals": 50,
    "local_price": 2850.00,
    "local_revenue": 142500.00,
    "comparisons": [
      {
        "district": {"code": "KL-TSR", "name": "Thrissur"},
        "distance_km": 75,
        "current_price": 2950.00,
        "gross_revenue": 147500.00,
        "transport_cost": 1625.00,
        "net_revenue": 145875.00,
        "net_gain_over_local": 3375.00,
        "recommendation": "recommended",
        "vehicle_type": "TRUCK_SMALL"
      },
      {
        "district": {"code": "KL-TVM", "name": "Thiruvananthapuram"},
        "distance_km": 220,
        "current_price": 2920.00,
        "gross_revenue": 146000.00,
        "transport_cost": 4300.00,
        "net_revenue": 141700.00,
        "net_gain_over_local": -800.00,
        "recommendation": "not_recommended",
        "vehicle_type": "TRUCK_LARGE"
      }
    ],
    "best_option": {
      "district": {"code": "KL-TSR", "name": "Thrissur"},
      "net_gain_over_local": 3375.00
    }
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `recommendation` | string | `recommended` or `not_recommended` |
| `vehicle_type` | string | `TEMPO`, `TRUCK_SMALL`, `TRUCK_LARGE` |
| `best_option` | object | District with highest net gain (null if none profitable) |

**Vehicle Selection Logic:**
- `TEMPO`: Quantity <= 2000 kg
- `TRUCK_SMALL`: Quantity <= 5000 kg
- `TRUCK_LARGE`: Quantity > 5000 kg

---

### 5.5 Community & Alert APIs

#### 5.5.1 List Posts

**`GET /posts`**

**Auth:** Required

**Query Parameters:**

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `limit` | integer | No | 20 (max: 50) |
| `cursor` | string | No | null |
| `type` | string | No | null (`post` or `alert`) |

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "pst_alert_001",
      "type": "alert",
      "title": "Heavy Rain Warning - Ernakulam District",
      "content": "IMD has issued heavy rain warning for Ernakulam...",
      "author": {
        "id": "usr_admin_001",
        "name": "AgriProfit Admin",
        "role": "admin"
      },
      "district": {"code": "KL-EKM", "name": "Ernakulam"},
      "highlight": true,
      "pinned": true,
      "pin_reason": "same_district",
      "created_at": "2026-01-19T08:00:00Z",
      "engagement": {"view_count": 1250}
    },
    {
      "id": "pst_post_001",
      "type": "post",
      "title": "Best practices for paddy storage",
      "content": "Sharing my experience with paddy storage...",
      "author": {
        "id": "usr_farmer_042",
        "name": "Rajan Pillai",
        "role": "farmer"
      },
      "district": {"code": "KL-ALP", "name": "Alappuzha"},
      "highlight": false,
      "pinned": false,
      "pin_reason": null,
      "created_at": "2026-01-17T10:15:00Z",
      "engagement": {"view_count": 342}
    }
  ],
  "pagination": {
    "limit": 20,
    "has_more": true,
    "next_cursor": "eyJpZCI6InBzdF9wb3N0XzAwMSJ9"
  }
}
```

**Backend-Computed Fields (Frontend NEVER computes these):**

| Field | Type | Description |
|-------|------|-------------|
| `highlight` | boolean | True for all alerts |
| `pinned` | boolean | True if alert is relevant to user's location |
| `pin_reason` | string | `same_district`, `neighboring_district`, `system_broadcast`, or null |

**Ordering Logic (Backend-controlled):**
1. Pinned alerts (same district) - newest first
2. Pinned alerts (neighboring district) - newest first
3. System broadcast alerts - newest first
4. Regular posts and non-pinned alerts - newest first

---

#### 5.5.2 Get Single Post

**`GET /posts/{post_id}`**

**Auth:** Required

**Response (200):** Same structure as single item in list

**Errors:** `UNAUTHORIZED` (401), `NOT_FOUND` (404)

---

#### 5.5.3 Create Post

**`POST /posts`**

**Auth:** Required

**Request:**
```json
{
  "type": "post",
  "title": "Best practices for paddy storage",
  "content": "Sharing my experience with paddy storage techniques..."
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `type` | string | Yes | `post` or `alert` |
| `title` | string | Yes | 5-200 characters |
| `content` | string | Yes | 10-5000 characters |

**Response (201):**
```json
{
  "success": true,
  "data": {
    "id": "pst_post_002",
    "type": "post",
    "title": "Best practices for paddy storage",
    "content": "Sharing my experience...",
    "author": {
      "id": "usr_farmer_042",
      "name": "Rajan Pillai",
      "role": "farmer"
    },
    "district": {"code": "KL-ALP", "name": "Alappuzha"},
    "highlight": false,
    "pinned": false,
    "pin_reason": null,
    "created_at": "2026-01-19T10:30:00Z",
    "engagement": {"view_count": 0}
  }
}
```

**Note:** `district` is automatically set from authenticated user's profile.

**Errors:** `VALIDATION_ERROR` (400), `UNAUTHORIZED` (401), `FORBIDDEN` (403 - profile incomplete)

---

#### 5.5.4 Delete Post

**`DELETE /posts/{post_id}`**

**Auth:** Required

Users can only delete their own posts. Admins can delete any post.

**Response (200):**
```json
{
  "success": true,
  "data": {"message": "Post deleted successfully"}
}
```

**Errors:** `UNAUTHORIZED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404)

---

### 5.6 Notification APIs

#### 5.6.1 List Notifications

**`GET /notifications`**

**Auth:** Required

**Query Parameters:**

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `limit` | integer | No | 20 (max: 50) |
| `cursor` | string | No | null |
| `unread_only` | boolean | No | false |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "unread_count": 3,
    "notifications": [
      {
        "id": "ntf_001",
        "type": "alert_nearby",
        "title": "Weather Alert in Your Area",
        "body": "Heavy rain warning issued for Ernakulam district",
        "read": false,
        "reference": {"type": "post", "id": "pst_alert_001"},
        "created_at": "2026-01-19T08:00:00Z"
      },
      {
        "id": "ntf_002",
        "type": "system_broadcast",
        "title": "New Feature Available",
        "body": "You can now compare transport costs",
        "read": true,
        "reference": null,
        "created_at": "2026-01-15T10:00:00Z"
      }
    ]
  },
  "pagination": {
    "limit": 20,
    "has_more": false,
    "next_cursor": null
  }
}
```

**Notification Types:**

| Type | Description |
|------|-------------|
| `alert_nearby` | Alert from same or neighboring district |
| `system_broadcast` | Admin broadcast message |

---

#### 5.6.2 Mark Notification as Read

**`POST /notifications/{notification_id}/read`**

**Auth:** Required

**Request:** None

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": "ntf_001",
    "read": true,
    "read_at": "2026-01-19T10:30:00Z"
  }
}
```

**Errors:** `UNAUTHORIZED` (401), `NOT_FOUND` (404)

---

#### 5.6.3 Mark All Notifications as Read

**`POST /notifications/read-all`**

**Auth:** Required

**Request:** None

**Response (200):**
```json
{
  "success": true,
  "data": {
    "marked_count": 3,
    "read_at": "2026-01-19T10:30:00Z"
  }
}
```

---

### 5.7 Admin APIs

**All endpoints require `admin` role.**

#### 5.7.1 Broadcast Alert

**`POST /admin/alerts/broadcast`**

**Auth:** Required (Admin only)

**Request:**
```json
{
  "title": "System Maintenance Notice",
  "content": "AgriProfit will undergo scheduled maintenance on January 25...",
  "target": "all"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `title` | string | Yes | 5-200 characters |
| `content` | string | Yes | 10-5000 characters |
| `target` | string | No | `all`, `state:{code}`, `district:{code}` (default: `all`) |

**Response (201):**
```json
{
  "success": true,
  "data": {
    "id": "pst_broadcast_001",
    "type": "alert",
    "title": "System Maintenance Notice",
    "content": "AgriProfit will undergo scheduled maintenance...",
    "author": {
      "id": "usr_admin_001",
      "name": "AgriProfit Admin",
      "role": "admin"
    },
    "broadcast": {
      "target": "all",
      "estimated_reach": 15420
    },
    "created_at": "2026-01-19T10:30:00Z",
    "notifications_queued": 15420
  }
}
```

**Errors:** `VALIDATION_ERROR` (400), `UNAUTHORIZED` (401), `FORBIDDEN` (403)

---

#### 5.7.2 Delete Any Post (Moderation)

**`DELETE /admin/posts/{post_id}`**

**Auth:** Required (Admin only)

**Request:**
```json
{
  "reason": "Inappropriate content violating community guidelines"
}
```

| Field | Type | Required |
|-------|------|----------|
| `reason` | string | Yes |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "message": "Post deleted successfully",
    "post_id": "pst_post_123",
    "deleted_by": "usr_admin_001",
    "reason": "Inappropriate content violating community guidelines",
    "deleted_at": "2026-01-19T10:30:00Z"
  }
}
```

---

#### 5.7.3 Get System Statistics

**`GET /admin/stats`**

**Auth:** Required (Admin only)

**Query Parameters:**

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `period` | string | No | `24h` (`24h`, `7d`, `30d`) |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "period": "24h",
    "generated_at": "2026-01-19T10:30:00Z",
    "users": {
      "total": 15420,
      "active_in_period": 3250,
      "new_in_period": 45
    },
    "posts": {
      "total": 8540,
      "created_in_period": 128,
      "alerts_in_period": 12
    },
    "api_usage": {
      "total_requests_in_period": 125000,
      "unique_users_in_period": 3250
    }
  }
}
```

---

## 6. Data Models

### 6.1 User

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Format: `usr_*` |
| `phone` | string | 10-digit phone |
| `role` | string | `farmer` or `admin` |
| `name` | string | Nullable |
| `district_code` | string | Nullable |
| `preferred_language` | string | `en` or `ml` |
| `profile_complete` | boolean | True if name and district set |

### 6.2 Commodity

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Format: `cmd_*` |
| `name` | string | English name |
| `name_ml` | string | Malayalam name |
| `category` | string | Category |
| `unit` | string | quintal, kg, count |

### 6.3 Post

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Format: `pst_*` |
| `type` | string | `post` or `alert` |
| `title` | string | Post title |
| `content` | string | Post content |
| `author_id` | string | Author user ID |
| `district_code` | string | Origin district |
| `highlight` | boolean | Backend-computed |
| `pinned` | boolean | Backend-computed |
| `pin_reason` | string | Backend-computed |

### 6.4 Notification

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Format: `ntf_*` |
| `user_id` | string | Recipient |
| `type` | string | `alert_nearby`, `system_broadcast` |
| `read` | boolean | Read status |
| `reference_type` | string | Nullable |
| `reference_id` | string | Nullable |

---

## 7. Appendix

### 7.1 District Codes (Kerala)

| Code | District |
|------|----------|
| `KL-TVM` | Thiruvananthapuram |
| `KL-KLM` | Kollam |
| `KL-PTA` | Pathanamthitta |
| `KL-ALP` | Alappuzha |
| `KL-KTM` | Kottayam |
| `KL-IDK` | Idukki |
| `KL-EKM` | Ernakulam |
| `KL-TSR` | Thrissur |
| `KL-PKD` | Palakkad |
| `KL-MLP` | Malappuram |
| `KL-KKD` | Kozhikode |
| `KL-WYD` | Wayanad |
| `KL-KNR` | Kannur |
| `KL-KSD` | Kasaragod |

### 7.2 Commodity Categories

| Category | Examples |
|----------|----------|
| `cereals` | Rice, Wheat |
| `pulses` | Lentils, Chickpeas |
| `vegetables` | Tomato, Onion |
| `fruits` | Banana, Mango |
| `spices` | Pepper, Cardamom |
| `plantation` | Coconut, Rubber |
| `oilseeds` | Groundnut, Mustard |

### 7.3 Transport Rate Reference

| Parameter | Value |
|-----------|-------|
| Base rate per km | ₹15.00 |
| Loading charges | ₹10.00/quintal (min ₹500) |
| Unloading charges | ₹10.00/quintal (min ₹500) |

### 7.4 ID Prefixes

| Prefix | Entity |
|--------|--------|
| `usr_` | User |
| `cmd_` | Commodity |
| `pst_` | Post |
| `ntf_` | Notification |
| `otp_req_` | OTP Request |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-19 | Initial release |

---

*This is the authoritative API contract. All implementations must adhere to this specification.*