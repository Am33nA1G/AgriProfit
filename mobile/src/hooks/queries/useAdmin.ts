import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';

export function useAdminStats() {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: () => adminApi.getStats(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useAdminUsers(search?: string) {
  return useQuery({
    queryKey: ['admin', 'users', search],
    queryFn: () => adminApi.getUsers(search),
    staleTime: 2 * 60 * 1000,
  });
}

export function useAdminPosts(search?: string) {
  return useQuery({
    queryKey: ['admin', 'posts', search],
    queryFn: () => adminApi.getPosts(search),
    staleTime: 2 * 60 * 1000,
  });
}

export function useAdminDeletePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: adminApi.deletePost,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'posts'] }),
  });
}

export function useAdminBroadcast() {
  return useMutation({
    mutationFn: adminApi.bulkNotifications,
  });
}
