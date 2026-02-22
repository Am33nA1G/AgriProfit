import apiClient from './client';
import type { Forecast } from '../types/models';

export const forecastsApi = {
  getForecastsForCommodity: (commodityId: string) =>
    apiClient.get<Forecast[]>(`/forecasts/${commodityId}`),
};
