import api from '@/lib/api';

export interface ForecastPoint {
    date: string;
    price_low: number | null;
    price_mid: number | null;
    price_high: number | null;
}

export interface ForecastResponse {
    commodity: string;
    district: string;
    horizon_days: number;
    direction: 'up' | 'down' | 'flat' | 'uncertain';
    price_low: number | null;
    price_mid: number | null;
    price_high: number | null;
    confidence_colour: 'Green' | 'Yellow' | 'Red';
    tier_label: string;
    last_data_date: string;
    forecast_points: ForecastPoint[];
    coverage_message: string | null;
    r2_score: number | null;
    data_freshness_days: number;
    is_stale: boolean;
    n_markets: number;
    typical_error_inr: number | null;
    mape_pct: number | null;
    model_version: string | null;
}

export const forecastService = {
    async getCommodities(): Promise<string[]> {
        const response = await api.get('/forecast/commodities');
        return response.data;
    },

    async getCommoditiesForDistrict(district: string): Promise<string[]> {
        const response = await api.get(`/forecast/commodities/${encodeURIComponent(district)}`);
        return response.data;
    },

    async getStatesForCommodity(commodity: string): Promise<string[]> {
        const response = await api.get(`/forecast/states/${encodeURIComponent(commodity)}`);
        return response.data;
    },

    async getDistrictsForCommodityState(commodity: string, state: string): Promise<string[]> {
        const response = await api.get(
            `/forecast/districts/${encodeURIComponent(commodity)}/${encodeURIComponent(state)}`
        );
        return response.data;
    },

    async getForecast(
        commodity: string,
        district: string,
        horizon: number = 14
    ): Promise<ForecastResponse> {
        const response = await api.get(
            `/forecast/${encodeURIComponent(commodity)}/${encodeURIComponent(district)}`,
            { params: { horizon } }
        );
        return response.data;
    },
};
