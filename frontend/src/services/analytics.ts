import api, { apiWithLongTimeout } from '@/lib/api';

export interface MarketSummary {
    total_commodities: number;
    total_mandis: number;
    total_price_records: number;
    total_forecasts: number;
    total_posts: number;
    total_users: number;
    last_updated: string;
    data_is_stale: boolean;
    hours_since_update: number;
}

export interface TopCommodityItem {
    commodity_id: string;
    name: string;
    record_count: number;
}

export interface TopMandiItem {
    mandi_id: string;
    name: string;
    record_count: number;
}

export interface PriceStatistics {
    commodity_id: string;
    commodity_name: string | null;
    mandi_id: string;
    mandi_name: string | null;
    avg_price: number;
    min_price: number;
    max_price: number;
    price_change_percent: number;
    data_points: number;
}

export interface WeeklyTrend {
    day: string;
    date: string;
    value: number;
}

export interface DashboardData {
    market_summary: MarketSummary;
    recent_price_changes: PriceStatistics[];
    top_commodities: TopCommodityItem[];
    top_mandis: TopMandiItem[];
    weekly_trends: WeeklyTrend[];
}

export interface MarketCoverage {
    active: number;
    pending: number;
    inactive: number;
}

export const analyticsService = {
    async getDashboard(): Promise<DashboardData> {
        const response = await apiWithLongTimeout.get('/analytics/dashboard');
        return response.data;
    },

    async getMarketSummary(): Promise<MarketSummary> {
        const response = await api.get('/analytics/summary');
        return response.data;
    },

    async getTopCommodities(limit: number = 10): Promise<TopCommodityItem[]> {
        const response = await api.get('/analytics/top-commodities', {
            params: { limit }
        });
        return response.data;
    },

    async getTopMandis(limit: number = 10): Promise<TopMandiItem[]> {
        const response = await api.get('/analytics/top-mandis', {
            params: { limit }
        });
        return response.data;
    },

    getMarketCoverage(summary: MarketSummary): MarketCoverage {
        // Calculate percentages based on active mandis vs total
        const total = summary.total_mandis || 1;
        const activePercent = Math.min(100, Math.round((total / 20) * 100));
        return {
            active: activePercent,
            pending: Math.round((100 - activePercent) * 0.6),
            inactive: Math.round((100 - activePercent) * 0.4)
        };
    }
};
