import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryApi } from '../../api/inventory';
import { useNetworkStore } from '../../store/networkStore';
import { enqueueOperation } from '../../services/offlineQueue';
import type { InventoryItem } from '../../types/models';

const KEY = ['inventory'];

export function useInventory() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => inventoryApi.getInventory(),
    staleTime: 60 * 1000,
  });
}

export function useAddInventory() {
  const qc = useQueryClient();
  const isConnected = useNetworkStore(s => s.isConnected);

  return useMutation({
    mutationFn: async (data: Parameters<typeof inventoryApi.addInventory>[0]) => {
      if (!isConnected) {
        // Enqueue for offline sync
        enqueueOperation('inventory_add', 'POST', '/inventory/', data);
        // Optimistic placeholder item
        const placeholder: Partial<InventoryItem> = {
          id: `offline_${Date.now()}`,
          commodity_id: (data as any).commodity_id,
          quantity: (data as any).quantity,
          unit: (data as any).unit,
          storage_date: new Date().toISOString().split('T')[0],
        };
        qc.setQueryData(KEY, (old: any) => ({
          ...old,
          data: [...(old?.data ?? []), placeholder],
        }));
        throw new Error('OFFLINE_QUEUED');
      }
      return inventoryApi.addInventory(data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
    onError: (err: Error) => {
      if (err.message === 'OFFLINE_QUEUED') return; // Don't propagate offline queued as error
    },
  });
}

export function useDeleteInventory() {
  const qc = useQueryClient();
  const isConnected = useNetworkStore(s => s.isConnected);

  return useMutation({
    mutationFn: async (id: string) => {
      if (!isConnected) {
        enqueueOperation('inventory_delete', 'DELETE', `/inventory/${id}`);
        return;
      }
      return inventoryApi.deleteInventory(id);
    },
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: KEY });
      const prev = qc.getQueryData(KEY);
      qc.setQueryData(KEY, (old: any) => ({
        ...old,
        data: old?.data?.filter((item: InventoryItem) => item.id !== id),
      }));
      return { prev };
    },
    onError: (_err: any, _id: any, context: any) => {
      if (context?.prev) qc.setQueryData(KEY, context.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useInventoryStock() {
  return useQuery({
    queryKey: ['inventory', 'stock'],
    queryFn: () => inventoryApi.getStock(),
    staleTime: 5 * 60 * 1000,
  });
}
