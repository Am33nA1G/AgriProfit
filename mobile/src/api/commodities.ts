import apiClient from './client';
import type { Commodity } from '../types/models';
import type { PaginatedResponse } from '../types/api';

export const commoditiesApi = {
  getCommoditiesWithPrices: (page = 1, limit = 20, category?: string) =>
    apiClient.get<PaginatedResponse<Commodity>>('/commodities/with-prices', {
      params: { page, limit, category },
    }),

  getCommodityDetail: (id: string) =>
    apiClient.get<Commodity>(`/commodities/${id}/details`),

  getCategories: () =>
    apiClient.get<string[]>('/commodities/categories'),

  searchCommodities: (query: string) =>
    apiClient.get<Commodity[]>('/commodities/search/', { params: { q: query } }),
};
