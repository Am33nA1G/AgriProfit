import api from "@/lib/api";

export interface MarketPrice {
    commodity_id: string;
    commodity: string;
    mandi_name: string;
    state: string;
    district: string;
    price_per_quintal: number;
    min_price: number;
    max_price: number;
    avg_7d: number | null;
    min_30d: number | null;
    max_30d: number | null;
    trend: 'up' | 'down' | 'stable';
    change_percent: number;
    change_amount: number;
    updated_at: string;
}

export interface HistoricalPrice {
    date: string;
    price: number;
}

export interface TopMover {
    commodity: string;
    change_percent: number;
    price: number;
}

export interface CurrentPricesParams {
    commodity?: string;
    state?: string;
    district?: string;
}

export interface HistoricalPricesParams {
    commodity: string;
    mandi_id: string;
    days: number;
}

export const pricesService = {
    async getCurrentPrices(params?: CurrentPricesParams): Promise<{ prices: MarketPrice[] }> {
        const response = await api.get('/prices/current', { params });
        return response.data;
    },

    async getHistoricalPrices(params: HistoricalPricesParams): Promise<{ data: HistoricalPrice[] }> {
        const response = await api.get('/prices/historical', { params });
        return response.data;
    },

    async getTopMovers(limit: number = 5): Promise<{ gainers: TopMover[], losers: TopMover[] }> {
        const response = await api.get('/prices/top-movers', { params: { limit } });
        return response.data;
    },

    async getPricesByMandi(mandiId: string, params?: { start_date?: string; end_date?: string; limit?: number }): Promise<any[]> {
        const response = await api.get(`/prices/mandi/${mandiId}`, { params: { limit: 100, ...params } });
        return response.data;
    }
};
