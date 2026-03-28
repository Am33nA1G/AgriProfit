# AgriProfit V1 - API Documentation

**Version**: 1.0  
**Last Updated**: February 2026  
**Base URL (Development)**: `http://localhost:8000`  
**Base URL (Production)**: `https://api.agriprofit.com`

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Common Patterns](#common-patterns)
4. [Endpoints by Module](#endpoints-by-module)
   - [Authentication](#module-authentication)
   - [Users](#module-users)
   - [Commodities](#module-commodities)
   - [Mandis](#module-mandis)
   - [Prices](#module-prices)
   - [Transport](#module-transport)
   - [Inventory](#module-inventory)
   - [Sales](#module-sales)
   - [Community](#module-community)
   - [Admin](#module-admin)
   - [Analytics](#module-analytics)
   - [Notifications](#module-notifications)
   - [Forecasts](#module-forecasts)
5. [Error Codes](#error-codes)
6. [Rate Limiting](#rate-limiting)

---

## Overview

AgriProfit API is a RESTful API built with FastAPI. It provides endpoints for managing agricultural commodities, mandi prices, user inventory, transport calculations, and community features.

### Key Features

- **OTP-based Authentication**: Secure phone-based login
- **Role-based Access**: User, Admin roles
- **Real-time Data**: Live mandi prices and commodity information
- **ML Recommendations**: Smart selling suggestions
- **Interactive Documentation**: Swagger UI at `/docs`

### Interactive Documentation

- **Swagger UI**: `{BASE_URL}/docs`
- **ReDoc**: `{BASE_URL}/redoc`
- **OpenAPI Schema**: `{BASE_URL}/openapi.json`

---

## Authentication

### Authentication Flow

AgriProfit uses OTP-based authentication with JWT tokens.

**Flow:**
1. Request OTP → Receive SMS with 6-digit code
2. Verify OTP → Receive JWT access token
3. Include token in `Authorization` header for protected endpoints

### JWT Token Format

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Details

- **Type**: Bearer token
- **Algorithm**: HS256
- **Expiration**: 24 hours (1440 minutes)
- **Location**: `Authorization` header

### Authentication Endpoints Summary

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/auth/request-otp` | POST | No | Request OTP code |
| `/auth/verify-otp` | POST | No | Verify OTP and get token |
| `/auth/complete-profile` | POST | Yes | Complete new user profile |
| `/auth/me` | GET | Yes | Get current user info |
| `/auth/logout` | POST | Yes | Logout (client-side token deletion) |

---

## Common Patterns

### Request Format

All requests use JSON:
```http
Content-Type: application/json
```

### Response Format

**Success Response:**
```json
{
  "id": "uuid-here",
  "field1": "value1",
  "field2": "value2"
}
```

**Error Response:**
```json
{
  "detail": "Error message here"
}
```

### Pagination

List endpoints support pagination:

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100, max: 1000)

**Example:**
```http
GET /commodities?skip=0&limit=50
```

**Response includes total count in some endpoints:**
```json
{
  "total": 250,
  "items": [...]
}
```

### Filtering & Search

Many endpoints support filtering:

**Example:**
```http
GET /mandis?state=Punjab&district=Ludhiana
GET /commodities?search=wheat&category=Grains
```

### Sorting

Some endpoints support sorting:

**Example:**
```http
GET /prices?sort_by=price&order=desc
```

---

## Endpoints by Module

## Module: Authentication

### 1. Request OTP

Request a 6-digit OTP code sent via SMS.

**Endpoint:** `POST /auth/request-otp`

**Authentication:** Not required

**Request Body:**
```json
{
  "phone_number": "9876543210"
}
```

**Validation:**
- Phone must be 10 digits
- Must start with 6, 7, 8, or 9
- Indian mobile numbers only

**Response:** `200 OK`
```json
{
  "message": "OTP sent successfully",
  "expires_in_minutes": 5
}
```

**Development Note:**  
For testing, if `TEST_OTP` is configured in environment, the OTP will be logged to console instead of sending SMS.

**Error Responses:**
- `422 Unprocessable Entity`: Invalid phone number format
- `429 Too Many Requests`: Rate limit exceeded

**Example:**
```bash
curl -X POST "http://localhost:8000/auth/request-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "9876543210"}'
```

---

### 2. Verify OTP

Verify OTP code and receive JWT access token.

**Endpoint:** `POST /auth/verify-otp`

**Authentication:** Not required

**Request Body:**
```json
{
  "phone_number": "9876543210",
  "otp": "123456"
}
```

**Response:** `200 OK`

**If user exists (registered):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "phone_number": "9876543210",
    "name": "Rajesh Kumar",
    "state": "Punjab",
    "district": "Ludhiana",
    "age": 35,
    "role": "user",
    "is_active": true,
    "created_at": "2026-01-15T10:30:00Z"
  },
  "is_new_user": false
}
```

**If new user (needs profile completion):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "phone_number": "9876543210",
    "is_active": true,
    "role": "user"
  },
  "is_new_user": true
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid OTP or expired
- `422 Unprocessable Entity`: Invalid format

**Example:**
```bash
curl -X POST "http://localhost:8000/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "9876543210",
    "otp": "123456"
  }'
```

---

### 3. Complete Profile

Complete user profile after first-time registration.

**Endpoint:** `POST /auth/complete-profile`

**Authentication:** Required (Bearer token from verify-otp)

**Request Body:**
```json
{
  "name": "Rajesh Kumar",
  "age": 35,
  "state": "Punjab",
  "district": "Ludhiana"
}
```

**Validation:**
- Name: 2-100 characters
- Age: 18-100
- State: Valid Indian state
- District: Valid district for the state

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "9876543210",
  "name": "Rajesh Kumar",
  "age": 35,
  "state": "Punjab",
  "district": "Ludhiana",
  "role": "user",
  "is_active": true,
  "created_at": "2026-02-08T10:30:00Z",
  "updated_at": "2026-02-08T10:35:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Not authenticated
- `400 Bad Request`: Profile already completed
- `422 Unprocessable Entity`: Invalid data

---

### 4. Get Current User

Get authenticated user's information.

**Endpoint:** `GET /auth/me`

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "9876543210",
  "name": "Rajesh Kumar",
  "age": 35,
  "state": "Punjab",
  "district": "Ludhiana",
  "role": "user",
  "is_active": true,
  "created_at": "2026-01-15T10:30:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Not authenticated or token expired

**Example:**
```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Module: Commodities

### 1. List Commodities

Get list of all commodities with optional filtering.

**Endpoint:** `GET /commodities`

**Authentication:** Not required

**Query Parameters:**
- `search` (string): Search by name
- `category` (string): Filter by category
- `skip` (int): Pagination offset (default: 0)
- `limit` (int): Results per page (default: 100, max: 1000)

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Wheat",
    "category": "Grains",
    "unit": "quintal",
    "created_at": "2026-01-01T00:00:00Z",
    "current_price": 2500.00,
    "price_change_1d": 2.5,
    "price_change_7d": -1.2,
    "price_change_30d": 5.8
  }
]
```

**Example:**
```bash
# Get all commodities
curl "http://localhost:8000/commodities"

# Search for wheat
curl "http://localhost:8000/commodities?search=wheat"

# Filter by category
curl "http://localhost:8000/commodities?category=Grains&limit=50"
```

---

### 2. Get Commodity Details

Get detailed information about a specific commodity.

**Endpoint:** `GET /commodities/{commodity_id}`

**Authentication:** Not required

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Wheat",
  "category": "Grains",
  "unit": "quintal",
  "description": "Common wheat variety",
  "created_at": "2026-01-01T00:00:00Z",
  "current_price": 2500.00,
  "price_stats": {
    "min_price": 2200.00,
    "max_price": 2800.00,
    "avg_price": 2500.00
  },
  "top_mandis": [
    {
      "mandi_name": "Ludhiana",
      "price": 2600.00
    }
  ]
}
```

**Error Responses:**
- `404 Not Found`: Commodity doesn't exist

---

### 3. Create Commodity (Admin)

Create a new commodity in the catalog.

**Endpoint:** `POST /commodities`

**Authentication:** Required (Admin role)

**Request Body:**
```json
{
  "name": "Tomato",
  "category": "Vegetables",
  "unit": "quintal"
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Tomato",
  "category": "Vegetables",
  "unit": "quintal",
  "created_at": "2026-02-08T10:30:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Admin role required
- `400 Bad Request`: Commodity already exists

---

## Module: Mandis

### 1. List Mandis

Get list of agricultural markets (mandis).

**Endpoint:** `GET /mandis`

**Authentication:** Not required

**Query Parameters:**
- `state` (string): Filter by state
- `district` (string): Filter by district
- `search` (string): Search by name
- `skip` (int): Pagination offset
- `limit` (int): Results per page

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Ludhiana Mandi",
    "state": "Punjab",
    "district": "Ludhiana",
    "address": "Main Market Road",
    "latitude": 30.9010,
    "longitude": 75.8573,
    "created_at": "2026-01-01T00:00:00Z"
  }
]
```

---

### 2. Get Mandi Details

Get detailed information about a specific mandi.

**Endpoint:** `GET /mandis/{mandi_id}`

**Authentication:** Not required

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Ludhiana Mandi",
  "state": "Punjab",
  "district": "Ludhiana",
  "address": "Main Market Road",
  "latitude": 30.9010,
  "longitude": 75.8573,
  "current_prices": [
    {
      "commodity_id": "abc-123",
      "commodity_name": "Wheat",
      "price": 2600.00,
      "date": "2026-02-08"
    }
  ]
}
```

---

## Module: Prices

### 1. Get Current Prices

Get current commodity prices at mandis.

**Endpoint:** `GET /prices/current`

**Authentication:** Not required

**Query Parameters:**
- `commodity_id` (UUID): Filter by commodity
- `mandi_id` (UUID): Filter by mandi
- `state` (string): Filter by state
- `limit` (int): Results per page

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "commodity_id": "abc-123",
    "commodity_name": "Wheat",
    "mandi_id": "def-456",
    "mandi_name": "Ludhiana Mandi",
    "price": 2600.00,
    "date": "2026-02-08",
    "created_at": "2026-02-08T06:00:00Z"
  }
]
```

---

### 2. Get Price History

Get historical price data for a commodity.

**Endpoint:** `GET /prices/history`

**Authentication:** Not required

**Query Parameters:**
- `commodity_id` (UUID, required): Commodity to get history for
- `mandi_id` (UUID, optional): Specific mandi
- `days` (int): Number of days (default: 30, max: 365)

**Response:** `200 OK`
```json
{
  "commodity_id": "abc-123",
  "commodity_name": "Wheat",
  "data": [
    {
      "date": "2026-02-08",
      "avg_price": 2550.00,
      "min_price": 2400.00,
      "max_price": 2650.00
    }
  ]
}
```

---

## Module: Transport

### 1. Calculate Transport Cost

Calculate transport cost between locations.

**Endpoint:** `POST /transport/calculate`

**Authentication:** Not required

**Request Body:**
```json
{
  "from_lat": 30.9010,
  "from_lon": 75.8573,
  "to_lat": 31.3260,
  "to_lon": 75.5762,
  "commodity_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity": 1000,
  "vehicle_type": "small_truck"
}
```

**Vehicle Types:**
- `pickup`: Small pickup truck
- `small_truck`: 1-2 ton capacity
- `medium_truck`: 3-5 ton capacity
- `large_truck`: 5-10 ton capacity

**Response:** `200 OK`
```json
{
  "distance_km": 125.5,
  "transport_cost": 2500.00,
  "fuel_cost": 1800.00,
  "driver_cost": 500.00,
  "other_costs": 200.00,
  "cost_per_km": 19.92,
  "estimated_time_hours": 2.5
}
```

---

## Module: Inventory

### 1. Get User Inventory

Get authenticated user's inventory items.

**Endpoint:** `GET /inventory`

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "commodity_id": "abc-123",
    "commodity_name": "Wheat",
    "quantity": 5000,
    "unit": "kg",
    "purchase_price": 2400.00,
    "purchase_date": "2026-01-15",
    "current_value": 12500000.00,
    "created_at": "2026-01-15T10:00:00Z"
  }
]
```

---

### 2. Add Inventory Item

Add a new item to user's inventory.

**Endpoint:** `POST /inventory`

**Authentication:** Required

**Request Body:**
```json
{
  "commodity_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity": 5000,
  "unit": "kg",
  "purchase_price": 2400.00,
  "purchase_date": "2026-01-15"
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "commodity_id": "abc-123",
  "commodity_name": "Wheat",
  "quantity": 5000,
  "unit": "kg",
  "purchase_price": 2400.00,
  "purchase_date": "2026-01-15",
  "created_at": "2026-01-15T10:00:00Z"
}
```

---

### 3. Delete Inventory Item

Remove an item from inventory.

**Endpoint:** `DELETE /inventory/{inventory_id}`

**Authentication:** Required

**Response:** `204 No Content`

**Error Responses:**
- `404 Not Found`: Inventory item doesn't exist
- `403 Forbidden`: Not the owner of this inventory item

---

## Module: Sales

### 1. Get User Sales

Get authenticated user's sales history.

**Endpoint:** `GET /sales`

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "commodity_id": "abc-123",
    "commodity_name": "Wheat",
    "mandi_id": "def-456",
    "mandi_name": "Ludhiana Mandi",
    "quantity": 1000,
    "unit": "kg",
    "sale_price": 2600.00,
    "sale_date": "2026-02-05",
    "total_amount": 2600000.00,
    "created_at": "2026-02-05T14:30:00Z"
  }
]
```

---

### 2. Log Sale

Record a commodity sale.

**Endpoint:** `POST /sales`

**Authentication:** Required

**Request Body:**
```json
{
  "commodity_id": "550e8400-e29b-41d4-a716-446655440000",
  "mandi_id": "def-456-789",
  "quantity": 1000,
  "unit": "kg",
  "sale_price": 2600.00,
  "sale_date": "2026-02-05"
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "commodity_id": "abc-123",
  "commodity_name": "Wheat",
  "mandi_id": "def-456",
  "mandi_name": "Ludhiana Mandi",
  "quantity": 1000,
  "sale_price": 2600.00,
  "sale_date": "2026-02-05",
  "total_amount": 2600000.00,
  "created_at": "2026-02-05T14:30:00Z"
}
```

---

## Module: Community

### 1. List Posts

Get community forum posts.

**Endpoint:** `GET /community/posts`

**Authentication:** Not required

**Query Parameters:**
- `category` (string): Filter by category
- `sort` (string): Sort order (latest, popular)
- `skip` (int): Pagination offset
- `limit` (int): Results per page

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Best time to sell wheat?",
    "content": "I have 5 tons of wheat...",
    "category": "Crop Management",
    "author_id": "user-123",
    "author_name": "Rajesh Kumar",
    "upvotes": 15,
    "reply_count": 3,
    "created_at": "2026-02-08T10:00:00Z"
  }
]
```

---

### 2. Create Post

Create a new community post.

**Endpoint:** `POST /community/posts`

**Authentication:** Required

**Request Body:**
```json
{
  "title": "Best time to sell wheat?",
  "content": "I have 5 tons of wheat in inventory...",
  "category": "Crop Management"
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Best time to sell wheat?",
  "content": "I have 5 tons of wheat...",
  "category": "Crop Management",
  "author_id": "user-123",
  "author_name": "Rajesh Kumar",
  "upvotes": 0,
  "reply_count": 0,
  "created_at": "2026-02-08T10:00:00Z"
}
```

---

### 3. Upvote Post

Upvote a community post.

**Endpoint:** `POST /community/posts/{post_id}/upvote`

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "post_id": "550e8400-e29b-41d4-a716-446655440000",
  "upvotes": 16,
  "user_upvoted": true
}
```

---

## Module: Admin

### 1. Get All Users (Admin)

Get list of all users for management.

**Endpoint:** `GET /admin/users`

**Authentication:** Required (Admin role)

**Query Parameters:**
- `search` (string): Search by name or phone
- `status` (string): Filter by status (active, banned)
- `skip` (int): Pagination offset
- `limit` (int): Results per page

**Response:** `200 OK`
```json
{
  "total": 1250,
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "phone_number": "9876543210",
      "name": "Rajesh Kumar",
      "state": "Punjab",
      "district": "Ludhiana",
      "role": "user",
      "is_active": true,
      "created_at": "2026-01-15T10:30:00Z"
    }
  ]
}
```

**Error Responses:**
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Admin role required

---

### 2. Ban User (Admin)

Ban a user from the platform.

**Endpoint:** `POST /admin/users/{user_id}/ban`

**Authentication:** Required (Admin role)

**Request Body:**
```json
{
  "reason": "Posting spam content"
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "is_active": false,
  "banned_at": "2026-02-08T14:30:00Z",
  "ban_reason": "Posting spam content"
}
```

---

### 3. Get Dashboard Stats (Admin)

Get platform statistics.

**Endpoint:** `GET /admin/stats`

**Authentication:** Required (Admin role)

**Response:** `200 OK`
```json
{
  "total_users": 1250,
  "active_users": 1200,
  "total_posts": 3500,
  "total_commodities": 45,
  "total_mandis": 520,
  "today_sales": 25,
  "today_registrations": 5
}
```

---

## Module: Analytics

### 1. Get Inventory Analysis

Get ML-powered analysis of user's inventory.

**Endpoint:** `GET /analytics/inventory`

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "recommendations": [
    {
      "commodity_name": "Wheat",
      "current_quantity": 5000,
      "recommended_action": "SELL",
      "confidence": 0.85,
      "reason": "Prices predicted to decrease in next 7 days",
      "best_mandi": "Ludhiana Mandi",
      "expected_price": 2650.00,
      "potential_profit": 50000.00
    }
  ],
  "total_value": 12750000.00,
  "analyzed_at": "2026-02-08T10:00:00Z"
}
```

---

## Module: Notifications

### 1. Get User Notifications

Get user's notifications.

**Endpoint:** `GET /notifications`

**Authentication:** Required

**Query Parameters:**
- `unread_only` (boolean): Filter unread notifications

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "price_alert",
    "title": "Wheat price increased!",
    "message": "Wheat price at Ludhiana increased to ₹2650/quintal",
    "is_read": false,
    "created_at": "2026-02-08T09:00:00Z"
  }
]
```

---

### 2. Mark as Read

Mark notification as read.

**Endpoint:** `PUT /notifications/{notification_id}/read`

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "is_read": true
}
```

---

## Module: Forecasts

### 1. Get Price Forecasts

Get ML price predictions for commodities.

**Endpoint:** `GET /forecasts/prices`

**Authentication:** Not required

**Query Parameters:**
- `commodity_id` (UUID): Commodity to forecast
- `days` (int): Forecast period (7, 15, 30 days)

**Response:** `200 OK`
```json
{
  "commodity_id": "abc-123",
  "commodity_name": "Wheat",
  "current_price": 2550.00,
  "forecasts": [
    {
      "date": "2026-02-09",
      "predicted_price": 2560.00,
      "confidence": 0.92,
      "trend": "increasing"
    }
  ]
}
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Delete successful |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Not authenticated or token invalid |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

**Validation Errors (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "phone_number"],
      "msg": "Phone number must start with 6, 7, 8, or 9",
      "type": "value_error"
    }
  ]
}
```

---

## Rate Limiting

AgriProfit API implements rate limiting to prevent abuse.

### Limits by Endpoint Type

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/auth/request-otp` | 3 requests | 1 minute |
| `/auth/verify-otp` | 5 requests | 1 minute |
| General API | 100 requests | 1 minute |
| Admin endpoints | 200 requests | 1 minute |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1675849200
```

### Rate Limit Exceeded Response

**Status:** `429 Too Many Requests`
```json
{
  "detail": "Rate limit exceeded. Please try again in 60 seconds."
}
```

---

## Best Practices

### 1. Authentication

- Store JWT token securely (httpOnly cookie or secure storage)
- Include token in all protected requests
- Handle 401 responses by redirecting to login
- Refresh token before expiry (within 24 hours)

### 2. Error Handling

```javascript
try {
  const response = await fetch('/api/endpoint', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  const data = await response.json();
  return data;
} catch (error) {
  console.error('API Error:', error.message);
}
```

### 3. Pagination

Always use pagination for list endpoints:
```javascript
const getAllCommodities = async () => {
  let allItems = [];
  let skip = 0;
  const limit = 100;
  
  while (true) {
    const items = await fetch(`/commodities?skip=${skip}&limit=${limit}`);
    allItems = [...allItems, ...items];
    
    if (items.length < limit) break;
    skip += limit;
  }
  
  return allItems;
};
```

---

## Support

For API support or questions:
- Check interactive docs: `{BASE_URL}/docs`
- Review this documentation
- Contact: [your-support-email]

---

**API Version**: 1.0  
**Last Updated**: February 2026  
**Status**: Production Ready ✅
