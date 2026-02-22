import apiClient from './client';
import type { User, CommunityPost } from '../types/models';

export const adminApi = {
  getStats: () =>
    apiClient.get<{
      total_users: number;
      total_posts: number;
      active_commodities: number;
      last_sync: string;
    }>('/admin/stats'),

  getUsers: (search?: string) =>
    apiClient.get<User[]>('/admin/users', { params: { search } }),

  getPosts: (search?: string) =>
    apiClient.get<CommunityPost[]>('/community/posts/', { params: { search, limit: 50 } }),

  deletePost: (id: string) =>
    apiClient.delete(`/community/posts/${id}`),

  banUser: (id: string) =>
    apiClient.put(`/admin/users/${id}/ban`),

  createNotification: (data: {
    user_id: string;
    title: string;
    message: string;
    notification_type: string;
  }) => apiClient.post('/notifications/', data),

  bulkNotifications: (data: {
    title: string;
    message: string;
    target_district?: string;
    notification_type: string;
  }) => apiClient.post('/notifications/bulk', data),
};
