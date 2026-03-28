import api from '@/lib/api';

export interface ArbitrageResult {
    mandi_name: string;
    district: string;
    state: string;
    distance_km: number;
    travel_time_hours: number;
    freight_cost_per_quintal: number;
    spoilage_percent: number;
    net_profit_per_quintal: number;
    verdict: string;              // "excellent" | "good" | "marginal" | "not_viable"
    is_interstate: boolean;
    price_date: string;           // ISO date string
    days_since_update: number;
    is_stale: boolean;
    stale_warning: string | null;
}

export interface ArbitrageResponse {
    commodity: string;
    origin_district: string;
    results: ArbitrageResult[];   // Max 3, sorted by net_profit_per_quintal desc
    suppressed_count: number;     // How many mandis were filtered by margin threshold
    threshold_pct: number;        // The threshold applied (default 10)
    data_reference_date: string;  // ISO date — what "fresh" means for this dataset
    has_stale_data: boolean;
    distance_note: string | null;
}

export const arbitrageService = {
    async getResults(commodity: string, district: string): Promise<ArbitrageResponse> {
        const response = await api.get<ArbitrageResponse>(
            `/arbitrage/${encodeURIComponent(commodity)}/${encodeURIComponent(district)}`
        );
        return response.data;
    },

    async getCommodities(): Promise<string[]> {
        const response = await api.get<string[]>('/arbitrage/commodities');
        return response.data;
    },

    async getStates(): Promise<string[]> {
        const response = await api.get<string[]>('/arbitrage/states');
        return response.data;
    },

    async getDistricts(state: string): Promise<string[]> {
        const response = await api.get<string[]>('/arbitrage/districts', {
            params: { state },
        });
        return response.data;
    },
};
