# Data Model: AgriProfit Mobile Application

**Branch**: `001-mobile-app` | **Date**: 2026-02-21

## Backend Addition: Device Push Token

This is the only new database entity. All other entities already exist in the backend.

### DevicePushToken (NEW — backend migration required)

| Field | Type | Nullable | Default | Notes |
|-------|------|----------|---------|-------|
| id | UUID | No | gen_random_uuid() | Primary key |
| user_id | UUID | No | — | FK → users.id, CASCADE delete |
| expo_push_token | String(255) | No | — | Expo push token (e.g., `ExponentPushToken[xxx]`) |
| device_platform | String(10) | No | — | `ios` or `android` |
| device_model | String(100) | Yes | — | e.g., "Samsung Galaxy A12" |
| app_version | String(20) | Yes | — | e.g., "1.0.0" |
| is_active | Boolean | No | true | Set false on logout or token invalidation |
| created_at | Timestamp | No | NOW() | |
| updated_at | Timestamp | No | NOW() | |

**Constraints**:
- Unique: (user_id, expo_push_token)
- Index: (user_id, is_active) — for querying active tokens per user
- Index: (expo_push_token) — for deduplication on token refresh
- Check: device_platform IN ('ios', 'android')

**Lifecycle**:
- Created on first login from a device
- Updated (token refresh) on each app launch and Expo token rotation
- Soft-deactivated (is_active=false) on logout
- Hard-deleted when Expo Push API returns `DeviceNotRegistered` error

### Example SQLAlchemy Model

```python
# backend/app/models/device_push_token.py
from sqlalchemy import Boolean, String, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, PG_UUID
import uuid
from datetime import datetime

class DevicePushToken(Base):
    __tablename__ = "device_push_tokens"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expo_push_token: Mapped[str] = mapped_column(String(255), nullable=False)
    device_platform: Mapped[str] = mapped_column(String(10), nullable=False)
    device_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="push_tokens")

    __table_args__ = (
        UniqueConstraint("user_id", "expo_push_token", name="uq_user_push_token"),
        CheckConstraint("device_platform IN ('ios', 'android')", name="ck_device_platform"),
    )
```

### Example Alembic Migration

```python
# alembic/versions/xxxx_add_device_push_tokens.py
def upgrade():
    op.create_table(
        "device_push_tokens",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", PG_UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expo_push_token", sa.String(255), nullable=False),
        sa.Column("device_platform", sa.String(10), nullable=False),
        sa.Column("device_model", sa.String(100), nullable=True),
        sa.Column("app_version", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP, server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("user_id", "expo_push_token", name="uq_user_push_token"),
        sa.CheckConstraint("device_platform IN ('ios', 'android')", name="ck_device_platform"),
    )
    op.create_index("idx_push_tokens_user_active", "device_push_tokens", ["user_id", "is_active"])
    op.create_index("idx_push_tokens_token", "device_push_tokens", ["expo_push_token"])

def downgrade():
    op.drop_table("device_push_tokens")
```

---

## Mobile-Side Data Models (TypeScript)

These represent the API response shapes and local state structures.

### Authentication

```typescript
interface User {
  id: string;           // UUID
  phone_number: string; // 10-digit Indian number
  name: string | null;
  role: 'farmer' | 'admin';
  district: string | null;
  state: string | null;
  language: string;     // 'en' | 'hi'
  is_profile_complete: boolean;
  created_at: string;   // ISO 8601
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  biometricEnabled: boolean;
  pinHash: string | null; // stored in SecureStore, not Zustand
}
```

### Commodities & Prices

```typescript
interface Commodity {
  id: string;
  name: string;
  category: string;
  is_active: boolean;
}

interface PriceRecord {
  id: string;
  commodity_id: string;
  mandi_id: string | null;
  mandi_name: string;
  price_date: string;       // YYYY-MM-DD
  price_min: number;
  price_max: number;
  price_modal: number;       // primary display price
}

interface PriceForecast {
  id: string;
  commodity_id: string;
  mandi_id: string | null;
  forecast_date: string;
  predicted_price: number;
  confidence: number;        // 0-1
  period_days: 7 | 30;
}

interface CommodityDetail {
  commodity: Commodity;
  latest_price: PriceRecord | null;
  price_history: PriceRecord[];
  forecasts: PriceForecast[];
  mandi_prices: MandiPrice[];
}

interface MandiPrice {
  mandi_id: string;
  mandi_name: string;
  state: string;
  district: string;
  price_modal: number;
  price_date: string;
}
```

### Mandis

```typescript
interface Mandi {
  id: string;
  name: string;
  market_code: string;
  state: string;
  district: string;
  latitude: number | null;
  longitude: number | null;
  is_active: boolean;
}
```

### Transport

```typescript
interface TransportCalculation {
  origin: string;
  destination_mandi: Mandi;
  commodity: Commodity;
  distance_km: number;
  transport_cost: number;
  commodity_price: number;
  net_profit: number;
}
```

### Inventory

```typescript
interface InventoryItem {
  id: string;
  user_id: string;
  commodity_id: string;
  commodity_name: string;
  quantity: number;
  unit: string;
  storage_date: string;
  estimated_value: number | null;
  created_at: string;
  updated_at: string;
}
```

### Sales

```typescript
interface SaleRecord {
  id: string;
  user_id: string;
  commodity_id: string;
  commodity_name: string;
  quantity: number;
  unit: string;
  sale_price: number;
  buyer_name: string | null;
  sale_date: string;
  created_at: string;
}

interface SalesAnalytics {
  total_revenue: number;
  total_sales: number;
  average_price: number;
  by_commodity: { commodity_name: string; total: number; count: number }[];
}
```

### Community

```typescript
interface CommunityPost {
  id: string;
  user_id: string;
  author_name: string;
  title: string;
  content: string;
  post_type: 'discussion' | 'question' | 'tip' | 'announcement' | 'alert';
  district: string | null;
  upvote_count: number;
  view_count: number;
  is_pinned: boolean;
  image_url: string | null;
  created_at: string;
  updated_at: string;
  reply_count: number;
}

interface CommunityReply {
  id: string;
  post_id: string;
  user_id: string;
  author_name: string;
  content: string;
  created_at: string;
}
```

### Notifications

```typescript
interface Notification {
  id: string;
  user_id: string;
  title: string | null;
  message: string;
  notification_type: 'price_alert' | 'forecast' | 'community' | 'system' | 'announcement';
  is_read: boolean;
  post_id: string | null;
  related_id: string | null;
  created_at: string;
  read_at: string | null;
}
```

### Offline Queue

```typescript
interface QueuedOperation {
  id: string;              // UUID, generated client-side
  type: 'CREATE' | 'UPDATE' | 'DELETE';
  endpoint: string;        // e.g., '/inventory/'
  method: 'POST' | 'PUT' | 'DELETE';
  payload: Record<string, unknown>;
  client_timestamp: string; // ISO 8601, for conflict detection
  retry_count: number;      // starts at 0, max 5
  status: 'pending' | 'syncing' | 'failed' | 'completed';
  error_message: string | null;
  created_at: string;
}
```

---

## Entity Relationships (Mobile Perspective)

```
User 1──* InventoryItem
User 1──* SaleRecord
User 1──* CommunityPost
User 1──* Notification
User 1──* DevicePushToken (backend)

Commodity 1──* PriceRecord
Commodity 1──* PriceForecast
Commodity 1──* InventoryItem
Commodity 1──* SaleRecord

Mandi 1──* PriceRecord
Mandi 1──* PriceForecast

CommunityPost 1──* CommunityReply
CommunityPost 1──* Notification (via post_id)
```
