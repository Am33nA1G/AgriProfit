import apiClient from './client';
import type { SaleRecord } from '../types/models';

export const salesApi = {
  getSales: () => apiClient.get<SaleRecord[]>('/sales/'),

  addSale: (data: {
    commodity_id: string;
    quantity: number;
    unit: string;
    sale_price: number;
    buyer_name?: string;
    sale_date?: string;
  }) => apiClient.post<SaleRecord>('/sales/', data),

  updateSale: (id: string, data: Partial<SaleRecord>) =>
    apiClient.put<SaleRecord>(`/sales/${id}`, data),

  deleteSale: (id: string) => apiClient.delete(`/sales/${id}`),

  getSalesAnalytics: () => apiClient.get('/sales/analytics'),
};
