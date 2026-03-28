import api from '@/lib/api';

export interface StressTestResult {
    worst_case_profit: number;
    break_even_price_per_kg: number;
    margin_of_safety_pct: number;
    verdict_survives_stress: boolean;
}

export interface CostBreakdown {
    transport_cost: number;
    toll_cost: number;
    loading_cost: number;
    unloading_cost: number;
    mandi_fee: number;
    commission: number;
    additional_cost: number;
    total_cost: number;
    // New logistics engine fields
    driver_bata: number;
    cleaner_bata: number;
    halt_cost: number;
    breakdown_reserve: number;
    permit_cost: number;
    rto_buffer: number;
    loading_hamali: number;
    unloading_hamali: number;
}

export interface MandiComparison {
    mandi_id: string | null;
    mandi_name: string;
    state: string;
    district: string;
    distance_km: number;
    price_per_kg: number;
    gross_revenue: number;
    costs: CostBreakdown;
    net_profit: number;
    profit_per_kg: number;
    roi_percentage: number;
    vehicle_type: 'TEMPO' | 'TRUCK_SMALL' | 'TRUCK_LARGE';
    vehicle_capacity_kg: number;
    trips_required: number;
    recommendation: 'recommended' | 'not_recommended';
    // Verdict
    verdict: string;
    verdict_reason: string;
    // Route
    travel_time_hours: number;
    route_type: string;
    is_interstate: boolean;
    diesel_price_used: number;
    // Spoilage
    spoilage_percent: number;
    weight_loss_percent: number;
    grade_discount_percent: number;
    net_saleable_quantity_kg: number;
    // Price analytics
    price_volatility_7d: number;
    price_trend: string;
    // Risk
    risk_score: number;
    confidence_score: number;
    stability_class: string;
    stress_test: StressTestResult | null;
    economic_warning: string | null;
}

export interface TransportCompareResponse {
    commodity: string;
    quantity_kg: number;
    source_district: string;
    comparisons: MandiComparison[];
    best_mandi: MandiComparison | null;
    total_mandis_analyzed: number;
    distance_note: string | null;
}

export interface CompareRequest {
    commodity: string;
    quantity_kg: number;
    source_state: string;
    source_district: string;
    max_distance_km?: number;
    limit?: number;
}

export const transportService = {
    async compareCosts(data: CompareRequest): Promise<TransportCompareResponse> {
        const response = await api.post('/transport/compare', data);
        return response.data;
    },

    async getStates(): Promise<string[]> {
        const response = await api.get('/mandis/states');
        return response.data;
    },

    async getDistricts(state: string): Promise<string[]> {
        const response = await api.get('/mandis/districts', { params: { state } });
        return response.data;
    },

    async getVehicles(): Promise<Record<string, { capacity_kg: number; cost_per_km: number; description: string }>> {
        const response = await api.get('/transport/vehicles');
        return response.data?.vehicles || {};
    },
};
