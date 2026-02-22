import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { commoditiesApi } from '../../api/commodities';

export const COMMODITIES_KEY = 'commodities';

export function useCommoditiesWithPrices(page = 1, category?: string) {
  return useQuery({
    queryKey: [COMMODITIES_KEY, 'withPrices', page, category],
    queryFn: () => commoditiesApi.getCommoditiesWithPrices(page, 20, category),
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useCommodityDetail(id: string) {
  return useQuery({
    queryKey: [COMMODITIES_KEY, 'detail', id],
    queryFn: () => commoditiesApi.getCommodityDetail(id),
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}

export function useCategories() {
  return useQuery({
    queryKey: [COMMODITIES_KEY, 'categories'],
    queryFn: () => commoditiesApi.getCategories(),
    staleTime: 30 * 60 * 1000,
  });
}

export function useSearchCommodities(query: string) {
  return useQuery({
    queryKey: [COMMODITIES_KEY, 'search', query],
    queryFn: () => commoditiesApi.searchCommodities(query),
    staleTime: 2 * 60 * 1000,
    enabled: query.length >= 2,
  });
}
