import { useQuery } from '@tanstack/react-query';
import { pricesApi } from '../../api/prices';

export function useHistoricalPrices(commodityId: string, days = 30) {
  return useQuery({
    queryKey: ['prices', 'historical', commodityId, days],
    queryFn: () => pricesApi.getHistoricalPrices(commodityId, days),
    staleTime: 5 * 60 * 1000,
    enabled: !!commodityId,
  });
}

export function useTopMovers() {
  return useQuery({
    queryKey: ['prices', 'topMovers'],
    queryFn: () => pricesApi.getTopMovers(),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePricesForCommodity(commodityId: string) {
  return useQuery({
    queryKey: ['prices', 'commodity', commodityId],
    queryFn: () => pricesApi.getPricesForCommodity(commodityId),
    staleTime: 5 * 60 * 1000,
    enabled: !!commodityId,
  });
}
