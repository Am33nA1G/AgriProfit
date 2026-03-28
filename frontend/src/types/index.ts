export interface User {
    id: string;
    phone_number: string;
    name?: string;
    age?: number;
    state?: string;
    district?: string;
    role: 'farmer' | 'trader' | 'admin';
    language: string;
    is_profile_complete: boolean;
    is_active?: boolean;
    created_at?: string;
}

export interface ProfileData {
    name: string;
    age: number;
    state: string;
    district: string;
}

export interface Commodity {
    id: string;
    name: string;
    name_local?: string;
    category: string;
    unit: string;
    description?: string;
    is_active?: boolean;
    created_at?: string;
    updated_at?: string;
    // Extended fields for display
    latest_price?: number;
    price_change?: number;
    mandi?: string;
}

// Extended commodity with price data from /commodities/with-prices
export interface CommodityWithPrice {
    id: string;
    name: string;
    name_local?: string;
    category?: string;
    unit?: string;
    description?: string;
    current_price?: number;
    last_updated?: string;
    price_change_1d?: number;
    price_change_7d?: number;
    price_change_30d?: number;
    is_in_season: boolean;
    peak_season?: string;
    major_states?: string[];
}

// Detailed commodity from /commodities/{id}/details
export interface CommodityDetail {
    id: string;
    name: string;
    name_local?: string;
    category?: string;
    unit?: string;
    description?: string;
    current_price?: number;
    price_changes: {
        "1d"?: number;
        "7d"?: number;
        "30d"?: number;
        "90d"?: number;
    };
    seasonal_info: {
        is_in_season: boolean;
        growing_months?: number[];
        harvest_months?: number[];
        peak_season_start?: number;
        peak_season_end?: number;
    };
    major_producing_states?: string[];
    price_history: { date: string; price: number }[];
    top_mandis: {
        name: string;
        state?: string;
        district?: string;
        price: number;
        as_of: string;
    }[];
    bottom_mandis: {
        name: string;
        state?: string;
        district?: string;
        price: number;
        as_of: string;
    }[];
}

// Paginated response for commodities with prices
export interface CommoditiesWithPriceResponse {
    commodities: CommodityWithPrice[];
    total: number;
    page: number;
    limit: number;
    has_more: boolean;
}

export interface Mandi {
    id: string;
    name: string;
    state: string;
    district: string;
    market_code?: string;
    address?: string;
    pincode?: string;
    latitude?: number;
    longitude?: number;
    is_active?: boolean;
    created_at?: string;
    updated_at?: string;
}

// Extended mandi from /mandis/with-filters
export interface MandiWithDistance {
    id: string;
    name: string;
    state: string;
    district: string;
    address?: string;
    market_code?: string;
    latitude?: number;
    longitude?: number;
    pincode?: string;
    phone?: string;
    email?: string;
    website?: string;
    opening_time?: string;
    closing_time?: string;
    operating_days?: string[];
    facilities: {
        weighbridge: boolean;
        storage: boolean;
        loading_dock: boolean;
        cold_storage: boolean;
    };
    payment_methods?: string[];
    commodities_accepted?: string[];
    rating?: number;
    total_reviews: number;
    distance_km?: number;
    top_prices: MandiPrice[];
}

export interface MandiPrice {
    commodity_id: string;
    commodity_name: string;
    unit?: string;
    modal_price: number;
    min_price?: number;
    max_price?: number;
    as_of: string;
    price_change_30d?: number;
}

// Detailed mandi from /mandis/{id}/details
export interface MandiDetail {
    id: string;
    name: string;
    state: string;
    district: string;
    address?: string;
    market_code?: string;
    pincode?: string;
    location: {
        latitude?: number;
        longitude?: number;
    };
    contact: {
        phone?: string;
        email?: string;
        website?: string;
    };
    operating_hours: {
        opening_time?: string;
        closing_time?: string;
        operating_days?: string[];
    };
    facilities: {
        weighbridge: boolean;
        storage: boolean;
        loading_dock: boolean;
        cold_storage: boolean;
    };
    payment_methods?: string[];
    commodities_accepted?: string[];
    rating?: number;
    total_reviews: number;
    distance_km?: number;
    current_prices: MandiPrice[];
}

// Paginated response for mandis with filters
export interface MandisWithFiltersResponse {
    mandis: MandiWithDistance[];
    total: number;
    page: number;
    limit: number;
    has_more: boolean;
}

export interface PriceHistory {
    id: number;
    commodity_id: number;
    mandi_id: number;
    date: string;
    min_price: number;
    max_price: number;
    modal_price: number;
    arrival_quantity?: number;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    is_new_user: boolean;
}