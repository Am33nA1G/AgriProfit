import apiClient from './client';
import type { TransportCalculation } from '../types/models';

export const transportApi = {
  calculateCost: (origin: string, destination: string, commodityId: string, quantity: number) =>
    apiClient.post<TransportCalculation>('/transport/calculate', {
      origin,
      destination,
      commodity_id: commodityId,
      quantity,
    }),

  compareMandis: (origin: string, commodityId: string, quantity: number) =>
    apiClient.post<TransportCalculation[]>('/transport/compare', {
      origin,
      commodity_id: commodityId,
      quantity,
    }),

  getVehicleTypes: () => apiClient.get<string[]>('/transport/vehicles'),

  getDistricts: () => apiClient.get<string[]>('/transport/districts'),
};
