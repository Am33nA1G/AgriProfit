import { useQuery } from '@tanstack/react-query';
import { forecastsApi } from '../../api/forecasts';

export function useForecasts(commodityId: string) {
  return useQuery({
    queryKey: ['forecasts', commodityId],
    queryFn: () => forecastsApi.getForecastsForCommodity(commodityId),
    staleTime: 10 * 60 * 1000,
    enabled: !!commodityId,
  });
}
