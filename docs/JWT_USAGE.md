# JWT Usage in AgriProfit

## What is JWT?

**JSON Web Token (JWT)** is a compact, self-contained token format used to securely transmit identity information between parties. A JWT has three Base64-encoded parts separated by dots:

```
header.payload.signature
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI8dXNlci1pZD4iLCJyb2xlIjoiZmFybWVyIiwiZXhwIjoxNzM5...}.<signature>
```

The server signs the token with a secret key. Any API endpoint can verify it **without hitting the database** — the signature proves the token is genuine.

---

## Why JWT is Used Here

AgriProfit uses **OTP (One-Time Password) phone authentication** — there are no passwords. After a user verifies their phone number with a 6-digit OTP, the server hands back a JWT. Every subsequent API request carries that JWT in the `Authorization` header, proving the user's identity without repeating the OTP flow.

JWT was chosen over session cookies because:
- The API is **stateless** — no server-side session store is needed.
- The frontend (Next.js) and mobile app can both attach the token to every request easily.
- The token itself carries the user's `id` and `role`, so the server can authorise without an extra DB lookup on every request.

---

## Where JWT is Created

### Library used
```
python-jose[cryptography]   ← backend/requirements.txt
```

### Configuration — `backend/app/core/config.py`
```
jwt_secret_key      ← random secret from .env (MUST be strong & secret)
jwt_algorithm       ← HS256 (HMAC-SHA256)
access_token_expire_minutes  ← controls token lifetime
```

### Token creation — `backend/app/auth/security.py`

```python
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,         # expiry — token is invalid after this
        "iss": "agriprofit-api",   # issuer — who created it
        "aud": "agriprofit-app",   # audience — who should use it
        "iat": datetime.now(timezone.utc),  # issued-at time
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**Payload claims stored inside the JWT:**

| Claim | Value | Purpose |
|-------|-------|---------|
| `sub` | user UUID | Identifies the user (no PII like phone number) |
| `role` | `"farmer"` / `"admin"` | Authorisation role |
| `exp` | UTC timestamp | Token expiry time |
| `iss` | `"agriprofit-api"` | Issuer verification |
| `aud` | `"agriprofit-app"` | Audience verification |
| `iat` | UTC timestamp | Issued-at time |

> **Security note:** Phone numbers are intentionally **not** stored in the JWT payload to avoid leaking PII if a token is decoded client-side.

### Token generation — `backend/app/auth/service.py`

```python
def generate_tokens(self, user: User) -> dict:
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

---

## When a JWT is Issued

The token is issued after successful OTP verification at:

**`POST /auth/verify-otp`** — `backend/app/auth/routes.py`

Flow:
1. User sends their phone number → server sends a 6-digit OTP via SMS.
2. User sends phone number + OTP → server verifies it (hashed in DB).
3. If valid, `generate_tokens(user)` creates the JWT.
4. A **refresh token** is also created (stored hashed in the `refresh_tokens` DB table).
5. Both tokens are returned to the client.

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "is_new_user": false
}
```

---

## Two-Token System

| Token | Lifetime | Stored where | Purpose |
|-------|----------|-------------|---------|
| **Access token** (JWT) | Short (minutes, configurable) | Frontend `localStorage` | Sent with every API request |
| **Refresh token** | 30 days | DB (`refresh_tokens` table, stored as a hash) | Used to get a new access token when it expires |

The **refresh token is not a JWT** — it is a random opaque string whose SHA-256 hash is stored in the database. This means it can be explicitly revoked (unlike a JWT which is valid until expiry).

---

## Where JWT is Verified (Backend)

### Token decoding — `backend/app/auth/security.py`

```python
def decode_token(token: str) -> dict | None:
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        audience="agriprofit-app",
        issuer="agriprofit-api",
    )
    return payload   # returns None on any JWTError
```

The library (`python-jose`) automatically rejects:
- Tokens with an invalid signature (tampered).
- Tokens past their `exp` claim (expired).
- Tokens with wrong `iss` or `aud` (issued by a different system).

### Auth dependency — `backend/app/auth/security.py`

```python
async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token.credentials)
    user_id = payload.get("sub")          # extract UUID from token
    user = db.query(User).filter(User.id == uuid_id, ...).first()
    if user.is_banned:
        raise HTTP 403                    # extra runtime check
    return user
```

**Every protected endpoint** uses `Depends(get_current_user)`. FastAPI injects this automatically, so route handlers receive a fully validated `User` object — no per-route token parsing needed.

### Optional auth — `get_current_user_optional`

Some public endpoints (e.g. commodity listings) can **optionally** use auth context without requiring it. They use `get_current_user_optional` which returns `None` for unauthenticated requests instead of raising a 401.

### Role-based access — `require_role` / `require_admin`

```python
def require_admin():
    return require_role("admin")

# Usage on a route:
@router.get("/admin/data")
def admin_only(current_user: User = Depends(require_admin())):
    ...
```

The `role` claim from the JWT payload is checked here — no extra DB query for role.

---

## Where JWT is Used (Frontend)

### Storage — `frontend/src/app/register/page.tsx`

After OTP verification succeeds, the token is stored in `localStorage`:

```typescript
localStorage.setItem('token', access_token);
```

### Attached to every request — `frontend/src/lib/api.ts`

The Axios instance has a **request interceptor** that reads the token and attaches it automatically:

```typescript
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});
```

Every API call from the frontend (inventory, sales, profile, etc.) automatically carries the `Authorization: Bearer <jwt>` header — no manual token handling needed per service file.

### Auto-logout on 401 — `frontend/src/lib/api.ts`

If the server returns `401 Unauthorized` (expired or invalid token):

```typescript
if (error.response?.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}
```

The user is automatically logged out and redirected to the login page.

---

## How It All Fits Together

```
User enters phone
      │
      ▼
POST /auth/request-otp   ──► SMS sent with 6-digit code
      │
User enters OTP
      │
      ▼
POST /auth/verify-otp    ──► Server verifies OTP hash
      │                       └─► create_access_token({sub: userId, role})
      │                       └─► create_refresh_token → stored in DB
      ▼
Client receives { access_token, refresh_token }
      │
      ▼
localStorage.setItem('token', access_token)
      │
Every API request:
      │  Authorization: Bearer <access_token>
      ▼
Backend get_current_user():
      │  decode_token() → verify signature, exp, iss, aud
      │  db.query(User).filter(id == sub)
      │  check is_banned
      ▼
Route handler receives validated User object
```

---

## Files Reference

| File | Role |
|------|------|
| `backend/app/auth/security.py` | `create_access_token`, `decode_token`, `get_current_user`, `get_current_user_optional`, `require_role`, refresh token helpers |
| `backend/app/auth/service.py` | `generate_tokens` — assembles the JWT payload |
| `backend/app/auth/routes.py` | `POST /auth/verify-otp` — issues token after OTP success |
| `backend/app/core/config.py` | `jwt_secret_key`, `jwt_algorithm`, `access_token_expire_minutes` |
| `frontend/src/lib/api.ts` | Axios interceptor — reads token from `localStorage`, attaches to every request, handles 401 auto-logout |
| `frontend/src/app/register/page.tsx` | Stores `access_token` in `localStorage` after login |
