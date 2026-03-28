import api from '@/lib/api';

export interface SaleItem {
    id: string;
    commodity_id: string;
    quantity: number;
    unit: string;
    price_per_unit: number;
    total_amount: number;
    buyer_name?: string;
    sale_date: string;
    commodity_name?: string;
}

export interface RecordSaleData {
    commodity_id: string;
    quantity: number;
    unit: string;
    price_per_unit: number;
    buyer_name?: string;
    sale_date?: string;
}

export interface SalesAnalytics {
    total_revenue: number;
    total_sales_count: number;
    top_selling_commodity: string | null;
}

export const salesService = {
    async getSalesHistory(): Promise<SaleItem[]> {
        const response = await api.get('/sales');
        return response.data;
    },

    async recordSale(data: RecordSaleData): Promise<SaleItem> {
        const response = await api.post('/sales', data);
        return response.data;
    },

    async deleteSale(id: string): Promise<void> {
        await api.delete(`/sales/${id}`);
    },

    async getAnalytics(): Promise<SalesAnalytics> {
        const response = await api.get('/sales/analytics');
        return response.data;
    }
};
