import apiClient from './client';
import type { PriceRecord } from '../types/models';

interface TopMovers {
  gainers: Array<{
    commodity: string;
    price: number;
    change_percent: number;
  }>;
  losers: Array<{
    commodity: string;
    price: number;
    change_percent: number;
  }>;
}

export const pricesApi = {
  getHistoricalPrices: (commodityId: string, days = 30) =>
    apiClient.get<PriceRecord[]>('/prices/historical', {
      params: { commodity_id: commodityId, days },
    }),

  getCurrentPrices: () =>
    apiClient.get<PriceRecord[]>('/prices/current'),

  getTopMovers: () =>
    apiClient.get<TopMovers>('/prices/top-movers'),

  getPricesForCommodity: (commodityId: string) =>
    apiClient.get<PriceRecord[]>(`/prices/commodity/${commodityId}`),
};
