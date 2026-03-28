# Mobile: Transport & Community Screens

**Date:** 2026-03-22
**Scope:** Add Transport and Community tabs to the React Native mobile app; restructure navigation from 4 to 5 tabs.

---

## 1. Navigation Restructure

### Before → After
**Before:** Inventory · Analyze · Forecast · Sales (4 tabs)
**After:** Inventory · Forecast · Transport · Community · Sales (5 tabs)

**The `Analyze` tab is removed from the bottom bar entirely.** `InventoryAnalysisScreen` is accessible only via the "Analyze →" button inside `InventoryScreen`.

**Tab icons (lucide-react-native):**

| Tab | Icon |
|-----|------|
| Inventory | `Archive` |
| Forecast | `TrendingUp` |
| Transport | `Truck` |
| Community | `Users` |
| Sales | `ShoppingCart` |

### Inventory tab
- `MainTabs.tsx` changes the Inventory tab component from `InventoryScreen` to `InventoryStack`.
- `InventoryStack` is a `createNativeStackNavigator<InventoryStackParamList>` with:
  - `InventoryScreen` as root (`headerShown: false`)
  - `InventoryAnalysisScreen` (`headerShown: true` — uses native stack header + default back button)
- `InventoryScreen` adds an "Analyze →" `TouchableOpacity` in its own header area that calls `navigation.navigate('InventoryAnalysis')`.
- **`InventoryAnalysisScreen` currently renders a custom `<View style={styles.header}>` block inside `SafeAreaView` (two occurrences at lines ~34 and ~85). Both must be removed** when this screen becomes a stack screen with `headerShown: true`, to avoid double-stacking the native header and the custom header. The native stack title should be set to `"Inventory Analysis"`.

### Community tab
- `MainTabs.tsx` mounts `CommunityStack` (not `CommunityFeedScreen`) as the Community tab component.
- `CommunityStack` is a `createNativeStackNavigator<CommunityStackParamList>` with:
  - `CommunityFeedScreen` as root (`headerShown: false`)
  - `PostDetailScreen` (`headerShown: true`, native back button)

### Navigation param types

```ts
// mobile/src/navigation/InventoryStack.tsx
export type InventoryStackParamList = {
    Inventory: undefined;
    InventoryAnalysis: undefined;
};

// mobile/src/navigation/CommunityStack.tsx
export type CommunityStackParamList = {
    CommunityFeed: undefined;
    PostDetail: { post_id: string };
};

// mobile/src/navigation/MainTabs.tsx — update existing MainTabsParamList
import { NavigatorScreenParams } from '@react-navigation/native';
export type MainTabsParamList = {
    Inventory: NavigatorScreenParams<InventoryStackParamList>;
    Forecast: undefined;
    Transport: undefined;
    Community: NavigatorScreenParams<CommunityStackParamList>;
    Sales: undefined;
};
```

---

## 2. Transport Screen

**File:** `mobile/src/screens/transport/TransportScreen.tsx`

### UI States
Local `results: MandiComparison[] | null`:
- `null` → form view
- `[]` → "No mandis found for this search." empty state
- non-empty array → results view

### Form state

| Field | Component | Notes |
|-------|-----------|-------|
| Commodity | `TextInput` + dropdown | Calls `GET /commodities/search/?q={term}&limit=20`; returns `CommodityResponse[]`; display `item.name`; send `item.name` (string) to transport API |
| Quantity | `TextInput` (numeric) + kg/quintal toggle | Screen converts: `quantity_kg = value × (unit === 'quintal' ? 100 : 1)`. Max 50,000 kg; show inline error if exceeded. Results always display weights in kg. |
| Source State | Modal picker | Static `STATE_DISTRICTS` map from `mobile/src/data/stateDistricts.ts`. Default: `"Kerala"`. |
| Source District | Modal picker | Filtered by selected state; resets to `""` when state changes; disabled until state is selected. |

**Validation on submit:** all fields required; show inline error text per field. Button disabled while loading.

**Error handling:**
- API error → `Alert.alert('Error', errorMessage)`
- Network failure → `Alert.alert('Error', 'Could not reach server. Check your connection.')`

### Results state

- **"Edit Search" button** at top: sets `results = null` (form values stay in component state, not reset).
- **`FlatList` of `MandiComparison` cards**, sorted as received from API (verdict tier → net profit within tier; do not client re-sort).
- **Each card shows:** mandi name + state, verdict badge, net profit (red if negative), ROI%, distance km, travel time hours.
- **Verdict badge colours:** `excellent`=green, `good`=blue, `marginal`=amber, `not_viable`=red.
- **Tap to expand inline:** shows cost breakdown from `costs` field (see `CostBreakdown` type below).

### TypeScript types (define in `mobile/src/services/transport.ts`)

```ts
export interface CostBreakdown {
    transport_cost: number;
    toll_cost: number;
    loading_cost: number;
    unloading_cost: number;
    mandi_fee: number;
    commission: number;
    additional_cost: number;
    driver_bata: number;
    cleaner_bata: number;
    halt_cost: number;
    breakdown_reserve: number;
    permit_cost: number;
    rto_buffer: number;
    loading_hamali: number;
    unloading_hamali: number;
    total_cost: number;
}

export interface MandiComparison {
    mandi_name: string;
    district: string;
    state: string;
    distance_km: number;
    price_per_kg: number;
    gross_revenue: number;
    net_profit: number;
    roi_percentage: number;        // e.g. 12.5 = 12.5%
    profit_per_kg: number;
    vehicle_type: string;
    vehicle_capacity_kg: number;
    trips_required: number;
    travel_time_hours: number;
    spoilage_percent: number;
    verdict: 'excellent' | 'good' | 'marginal' | 'not_viable';
    verdict_reason: string;
    costs: CostBreakdown;
    risk_score: number;
    confidence_score: number;
    economic_warning: string | null;
}
```

The `TransportCompareResponse` wraps comparisons in an envelope:

```ts
interface TransportCompareResponse {
    comparisons: MandiComparison[];
}
```

### Service: `mobile/src/services/transport.ts`

```ts
import api from '../lib/api';  // JWT auto-attached

async compare(params: {
    commodity: string;
    quantity_kg: number;
    source_state: string;
    source_district: string;
}): Promise<MandiComparison[]> {
    const { data } = await api.post('/transport/compare', params);
    return data.comparisons;   // unwrap envelope
}
```

---

## 3. Community Screens

### 3a. CommunityFeedScreen

**File:** `mobile/src/screens/community/CommunityFeedScreen.tsx`

**Category chips** (horizontal `ScrollView`, not `FlatList`):

| Chip label | `post_type` param |
|------------|-------------------|
| All        | *(omit param)*    |
| General    | `discussion`      |
| Tips       | `tip`             |
| Questions  | `question`        |
| Alert      | `alert`           |

`announcement` is excluded (admin-created content; not shown in mobile chips).

**Sort** (client-side only; applied after fetch; preserved across pull-to-refresh):

| Label        | Sort key on `CommunityPost` |
|--------------|-----------------------------|
| Most Recent  | `created_at` desc           |
| Most Upvoted | `likes_count` desc          |
| Most Replies | `replies_count` desc        |

**Post feed:** `FlatList` of `CommunityPost` cards. Each card: title, category badge (colour from `POST_TYPE_COLORS`), `author_name`, relative time, `likes_count` (heart icon), `replies_count` (comment icon).

**Fetch:** `listPosts({ post_type?, limit: 100 })` — cap at 100 posts to bound payload in v1.

**Pull-to-refresh:** re-fetches and re-applies current sort without resetting sort selection.

**Error state:** show "Failed to load posts. Pull to retry." with retry button.

**FAB** ("+" `TouchableOpacity`, bottom-right): opens Create Post bottom sheet.

**Create Post bottom sheet:**
- Title: required, min 1 char, max 200 chars
- Content: required, min 10 chars (backend minimum), max 2000 chars (mobile UX limit; backend allows 10,000 but 2000 is sufficient for mobile)
- Category picker: General / Tip / Question / Alert
- Submit → `createPost(...)`. On success: dismiss sheet, prepend new post to local list.
- No image upload (non-goal; `expo-image-picker` not installed).

### 3b. PostDetailScreen

**File:** `mobile/src/screens/community/PostDetailScreen.tsx`

Receives `{ post_id: string }` via `route.params.post_id`.

On mount: fetch post (`GET /community/posts/{post_id}`). Show loading spinner; show error message on failure.

**Image:** if `post.image_url !== null`, render `<Image source={{ uri: post.image_url }} />`; if null, render nothing.

**Upvote toggle (optimistic update):**
1. Flip `liked` state and adjust `likesCount` immediately.
2. Call API:
   - Was not liked → `POST /community/posts/{post_id}/upvote`
   - Was liked → `DELETE /community/posts/{post_id}/upvote`
3. On API error: rollback both `liked` and `likesCount` to pre-tap values + `Alert.alert('Failed to update')`.
- Button renders filled heart when liked, outline heart when not.

**Replies:**
- Fetch on mount: `GET /community/posts/{post_id}/replies` (all replies, no pagination in v1).
- Show loading spinner while fetching. Show author name, content, relative time per reply.
- Reply input pinned at bottom (`KeyboardAvoidingView`).
- Submit → `addReply(post_id, content)`. On success: append to local reply list; clear input.

**Ownership and "⋮" menu:**
- `currentUserId` from Zustand: `useAuthStore(s => s.user?.id)` (type: `string | undefined`; `AuthUser.id` is a `string`).
- Show "⋮" menu only when `post.user_id === currentUserId && currentUserId !== undefined`.
- **Edit:** opens the same bottom sheet as Create Post, pre-filled with `post.title`, `post.content`, `post.post_type`. On submit → `updatePost(post_id, data)`. On success: update local post state with returned post.
- **Delete:** `Alert.alert('Delete Post', 'Are you sure?', [{ text: 'Cancel' }, { text: 'Delete', style: 'destructive', onPress }])`. On confirm → `deletePost(post_id)`. On success: `navigation.goBack()`.

### TypeScript types (define in `mobile/src/services/community.ts`)

Mirror `frontend/src/services/community.ts`:

```ts
export type PostType = 'discussion' | 'question' | 'tip' | 'announcement' | 'alert';

export const POST_TYPE_LABELS: Record<PostType, string> = {
    discussion: 'General',
    question: 'Question',
    tip: 'Tip',
    announcement: 'Announcement',
    alert: 'Alert',
};

export const POST_TYPE_COLORS: Record<PostType, string> = {
    discussion: '#3b82f6',   // blue
    question: '#22c55e',     // green
    tip: '#a855f7',          // purple
    announcement: '#f97316', // orange
    alert: '#ef4444',        // red
};

export interface CommunityPost {
    id: string;
    title: string;
    content: string;
    user_id: string;
    post_type: PostType;
    district: string | null;
    image_url: string | null;
    likes_count: number;
    replies_count: number;
    user_has_liked: boolean;
    created_at: string;
    updated_at: string;
    author_name?: string;
}

export interface CommunityReply {
    id: string;
    post_id: string;
    user_id: string;
    content: string;
    created_at: string;
    author_name?: string;
}
```

### Service: `mobile/src/services/community.ts`

All methods use `api` from `mobile/src/lib/api.ts` (JWT auto-attached).

```ts
// 1. GET /community/posts?post_type={type}&limit={n}
// Backend returns paginated envelope { items, total, skip, limit } — extract .items
async listPosts(params?: { post_type?: PostType; limit?: number }): Promise<CommunityPost[]> {
    const { data } = await api.get('/community/posts', { params });
    return data.items;
}

// 2. POST /community/posts
async createPost(payload: { title: string; content: string; post_type: PostType }): Promise<CommunityPost>

// 3. PUT /community/posts/{id}
async updatePost(id: string, payload: { title?: string; content?: string; post_type?: PostType }): Promise<CommunityPost>

// 4. DELETE /community/posts/{id}
async deletePost(id: string): Promise<void>

// 5. POST /community/posts/{post_id}/upvote
async addUpvote(post_id: string): Promise<void>

// 6. DELETE /community/posts/{post_id}/upvote
async removeUpvote(post_id: string): Promise<void>

// 7. GET /community/posts/{post_id}/replies
async getReplies(post_id: string): Promise<CommunityReply[]>

// 8. POST /community/posts/{post_id}/reply   ← singular "reply", not "replies"
async addReply(post_id: string, content: string): Promise<CommunityReply>
```

---

## 4. Files to Create / Modify

| Action | File | Key change |
|--------|------|------------|
| Modify | `mobile/src/navigation/MainTabs.tsx` | Update `MainTabsParamList`; mount `InventoryStack` + `CommunityStack`; drop `Analyze` tab; add Transport + Community tabs with Truck + Users icons |
| Create | `mobile/src/navigation/InventoryStack.tsx` | Native stack with `InventoryScreen` + `InventoryAnalysisScreen` |
| Create | `mobile/src/navigation/CommunityStack.tsx` | Native stack with `CommunityFeedScreen` + `PostDetailScreen` |
| Modify | `mobile/src/screens/inventory/InventoryScreen.tsx` | Add "Analyze →" button in header |
| Modify | `mobile/src/screens/inventory/InventoryAnalysisScreen.tsx` | Remove both inline `<View style={styles.header}>` blocks; screen now uses native stack header (`headerShown: true` in stack options, title = "Inventory Analysis") |
| Create | `mobile/src/screens/transport/TransportScreen.tsx` | Form + results views |
| Create | `mobile/src/screens/community/CommunityFeedScreen.tsx` | Feed + FAB + create bottom sheet |
| Create | `mobile/src/screens/community/PostDetailScreen.tsx` | Full post + replies + upvote + edit/delete |
| Create | `mobile/src/services/transport.ts` | `compare()` — unwraps `data.comparisons` |
| Create | `mobile/src/services/community.ts` | 8 API methods |
| Create | `mobile/src/data/stateDistricts.ts` | Static `STATE_DISTRICTS` map (copy from web) |

---

## 5. Non-Goals

- Push notifications for community replies (future).
- Offline caching (future).
- Transport cost settings override on mobile (desktop only).
- Image upload for community posts (`expo-image-picker` not installed; display-only).
- Pagination for community feed or replies (single-page load, limit=100 for v1).
- Backend `sort_by` parameter for community feed (client-side sort only).
- Deep linking / custom Android back-press handling (uses default RN behaviour).
- Community search (future).
