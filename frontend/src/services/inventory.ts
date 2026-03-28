import api from '@/lib/api';

export interface InventoryItem {
    id: string;
    user_id: string;
    commodity_id: string;
    quantity: number;
    unit: string;
    commodity_name?: string;
    updated_at: string;
}

export interface AddInventoryData {
    commodity_id: string;
    quantity: number;
    unit: string;
}

export interface MandiRecommendation {
    mandi_id: string;
    mandi_name: string;
    state: string;
    district: string;
    modal_price: number;
    min_price: number;
    max_price: number;
    price_date: string;
    estimated_revenue: number;
    estimated_min_revenue: number;
    estimated_max_revenue: number;
    is_local: boolean;
    // Transport-aware fields (populated when user location is known)
    distance_km?: number | null;
    transport_cost?: number | null;
    net_profit?: number | null;
    verdict?: string | null;
    verdict_reason?: string | null;
}

export interface CommodityAnalysis {
    commodity_id: string;
    commodity_name: string;
    quantity: number;
    unit: string;
    best_mandis: MandiRecommendation[];
    recommended_mandi?: string;
    recommended_price?: number;
    estimated_min_revenue: number;
    estimated_max_revenue: number;
    message?: string;
}

export interface InventoryAnalysisResponse {
    total_items: number;
    analysis: CommodityAnalysis[];
    total_estimated_min_revenue: number;
    total_estimated_max_revenue: number;
}

export const inventoryService = {
    async getInventory(): Promise<InventoryItem[]> {
        const response = await api.get('/inventory');
        return response.data;
    },

    async addInventory(data: AddInventoryData): Promise<InventoryItem> {
        const response = await api.post('/inventory', data);
        return response.data;
    },

    async deleteInventory(id: string): Promise<void> {
        await api.delete(`/inventory/${id}`);
    },

    async analyzeInventory(): Promise<InventoryAnalysisResponse> {
        const response = await api.post('/inventory/analyze');
        return response.data;
    }
};
