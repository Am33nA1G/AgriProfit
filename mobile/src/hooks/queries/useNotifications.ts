import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { notificationsApi } from '../../api/notifications';
import type { Notification } from '../../types/models';

const NOTIF_KEY = ['notifications'];

export function useNotifications(page = 1, isRead?: boolean) {
  return useQuery({
    queryKey: [...NOTIF_KEY, page, isRead],
    queryFn: () => notificationsApi.getNotifications(page, isRead),
    staleTime: 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: [...NOTIF_KEY, 'unreadCount'],
    queryFn: () => notificationsApi.getUnreadCount(),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: NOTIF_KEY });
      // Optimistic: mark as read in cache
      qc.setQueriesData({ queryKey: NOTIF_KEY }, (old: any) => {
        if (!old?.data?.items) return old;
        return {
          ...old,
          data: {
            ...old.data,
            items: old.data.items.map((n: Notification) =>
              n.id === id ? { ...n, is_read: true } : n,
            ),
          },
        };
      });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: NOTIF_KEY }),
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: NOTIF_KEY }),
  });
}

export function useDeleteNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.deleteNotification(id),
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: NOTIF_KEY });
      qc.setQueriesData({ queryKey: NOTIF_KEY }, (old: any) => {
        if (!old?.data?.items) return old;
        return {
          ...old,
          data: {
            ...old.data,
            items: old.data.items.filter((n: Notification) => n.id !== id),
          },
        };
      });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: NOTIF_KEY }),
  });
}
