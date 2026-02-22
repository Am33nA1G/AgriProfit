import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { salesApi } from '../../api/sales';
import { useNetworkStore } from '../../store/networkStore';
import { enqueueOperation } from '../../services/offlineQueue';
import type { SaleRecord } from '../../types/models';

const KEY = ['sales'];

export function useSales() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => salesApi.getSales(),
    staleTime: 60 * 1000,
  });
}

export function useAddSale() {
  const qc = useQueryClient();
  const isConnected = useNetworkStore(s => s.isConnected);

  return useMutation({
    mutationFn: async (data: Parameters<typeof salesApi.addSale>[0]) => {
      if (!isConnected) {
        enqueueOperation('sale_add', 'POST', '/sales/', data);
        // Optimistic placeholder
        const placeholder: Partial<SaleRecord> = {
          id: `offline_${Date.now()}`,
          commodity_id: (data as any).commodity_id,
          quantity: (data as any).quantity,
          unit: (data as any).unit,
          sale_price: (data as any).sale_price,
          sale_date: (data as any).sale_date ?? new Date().toISOString().split('T')[0],
        };
        qc.setQueryData(KEY, (old: any) => ({
          ...old,
          data: [...(old?.data ?? []), placeholder],
        }));
        throw new Error('OFFLINE_QUEUED');
      }
      return salesApi.addSale(data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ['sales', 'analytics'] });
    },
    onError: (err: Error) => {
      if (err.message === 'OFFLINE_QUEUED') return;
    },
  });
}

export function useDeleteSale() {
  const qc = useQueryClient();
  const isConnected = useNetworkStore(s => s.isConnected);

  return useMutation({
    mutationFn: async (id: string) => {
      if (!isConnected) {
        enqueueOperation('sale_delete', 'DELETE', `/sales/${id}`);
        return;
      }
      return salesApi.deleteSale(id);
    },
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: KEY });
      const prev = qc.getQueryData(KEY);
      qc.setQueryData(KEY, (old: any) => ({
        ...old,
        data: old?.data?.filter((item: SaleRecord) => item.id !== id),
      }));
      return { prev };
    },
    onError: (_err: any, _id: any, context: any) => {
      if (context?.prev) qc.setQueryData(KEY, context.prev);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ['sales', 'analytics'] });
    },
  });
}

export function useSalesAnalytics() {
  return useQuery({
    queryKey: ['sales', 'analytics'],
    queryFn: () => salesApi.getSalesAnalytics(),
    staleTime: 5 * 60 * 1000,
  });
}
