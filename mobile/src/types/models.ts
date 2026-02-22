// Core domain models matching backend API responses

export interface User {
  id: string;
  phone_number: string;
  name: string | null;
  state: string | null;
  district: string | null;
  role: 'farmer' | 'admin';
  is_active: boolean;
  is_profile_complete: boolean;
  created_at: string;
  updated_at: string;
}

export interface Commodity {
  id: string;
  name: string;
  category: string;
  unit: string;
  description: string | null;
  is_active: boolean;
  current_price?: number | null;
  price_change?: number | null;
  price_change_pct?: number | null;
  last_updated?: string | null;
}

export interface PriceRecord {
  id: string;
  commodity_id: string;
  commodity_name: string;
  mandi_id: string | null;
  mandi_name: string;
  district: string;
  state: string;
  price_min: number;
  price_max: number;
  price_modal: number;
  price_date: string;
  created_at: string;
}

export interface Mandi {
  id: string;
  name: string;
  market_code: string;
  state: string;
  district: string;
  latitude: number | null;
  longitude: number | null;
  is_active: boolean;
  created_at: string;
}

export interface Forecast {
  id: string;
  commodity_id: string;
  commodity_name: string;
  predicted_price: number;
  confidence: number;
  forecast_date: string;
  forecast_type: '7day' | '30day';
  created_at: string;
}

export interface InventoryItem {
  id: string;
  user_id: string;
  commodity_id: string;
  commodity_name: string;
  quantity: number;
  unit: string;
  storage_date: string;
  notes: string | null;
  market_value?: number | null;
  created_at: string;
  updated_at: string;
}

export interface SaleRecord {
  id: string;
  user_id: string;
  commodity_id: string;
  commodity_name: string;
  quantity: number;
  unit: string;
  sale_price: number;
  total_amount: number;
  buyer_name: string | null;
  sale_date: string;
  created_at: string;
  updated_at: string;
}

export interface CommunityPost {
  id: string;
  user_id: string;
  author_name: string;
  title: string;
  content: string;
  post_type: 'discussion' | 'question' | 'tip' | 'alert';
  district: string | null;
  state: string | null;
  upvote_count: number;
  reply_count: number;
  is_pinned: boolean;
  user_has_upvoted?: boolean;
  created_at: string;
  updated_at: string;
}

export interface CommunityReply {
  id: string;
  post_id: string;
  user_id: string;
  author_name: string;
  content: string;
  upvote_count: number;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  notification_type: 'price_alert' | 'community' | 'system' | 'announcement';
  is_read: boolean;
  data: Record<string, string> | null;
  created_at: string;
}

export interface TransportCalculation {
  mandi_id: string;
  mandi_name: string;
  district: string;
  state: string;
  distance_km: number;
  transport_cost: number;
  commodity_price: number;
  net_profit: number;
  vehicle_type: string;
}
