import apiClient from './client';
import type { InventoryItem } from '../types/models';

export const inventoryApi = {
  getInventory: () => apiClient.get<InventoryItem[]>('/inventory/'),

  addInventory: (data: {
    commodity_id: string;
    quantity: number;
    unit: string;
    storage_date?: string;
  }) => apiClient.post<InventoryItem>('/inventory/', data),

  updateInventory: (id: string, data: Partial<InventoryItem>) =>
    apiClient.put<InventoryItem>(`/inventory/${id}`, data),

  deleteInventory: (id: string) => apiClient.delete(`/inventory/${id}`),

  getStock: () => apiClient.get('/inventory/stock'),

  analyzeInventory: () => apiClient.post('/inventory/analyze', {}),
};
