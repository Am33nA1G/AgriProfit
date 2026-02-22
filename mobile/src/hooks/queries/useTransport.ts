import { useQuery, useMutation } from '@tanstack/react-query';
import { transportApi } from '../../api/transport';

export function useTransportCompare() {
  return useMutation({
    mutationFn: ({
      origin,
      commodityId,
      quantity,
    }: {
      origin: string;
      commodityId: string;
      quantity: number;
    }) => transportApi.compareMandis(origin, commodityId, quantity),
  });
}

export function useVehicleTypes() {
  return useQuery({
    queryKey: ['transport', 'vehicles'],
    queryFn: () => transportApi.getVehicleTypes(),
    staleTime: 60 * 60 * 1000,
  });
}

export function useTransportDistricts() {
  return useQuery({
    queryKey: ['transport', 'districts'],
    queryFn: () => transportApi.getDistricts(),
    staleTime: 60 * 60 * 1000,
  });
}
