// mobile/src/services/transport.ts
// Transport mandi-comparison API service.

import api from '../lib/api';

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
    roi_percentage: number;
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

export interface TransportCompareParams {
    commodity: string;
    quantity_kg: number;
    source_state: string;
    source_district: string;
}

export const transportService = {
    async compare(params: TransportCompareParams): Promise<MandiComparison[]> {
        const { data } = await api.post('/transport/compare', params);
        return data.comparisons;
    },
};
