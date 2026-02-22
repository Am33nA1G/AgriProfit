import apiClient from './client';
import type { Notification } from '../types/models';
import type { PaginatedResponse } from '../types/api';

export const notificationsApi = {
  getNotifications: (page = 1, isRead?: boolean) =>
    apiClient.get<PaginatedResponse<Notification>>('/notifications/', {
      params: { skip: (page - 1) * 20, limit: 20, is_read: isRead },
    }),

  getUnreadCount: () =>
    apiClient.get<{ unread_count: number }>('/notifications/unread-count'),

  markRead: (id: string) =>
    apiClient.put<Notification>(`/notifications/${id}/read`),

  markAllRead: () =>
    apiClient.put('/notifications/read-all'),

  deleteNotification: (id: string) =>
    apiClient.delete(`/notifications/${id}`),

  registerPushToken: (
    token: string,
    platform: 'ios' | 'android',
    model?: string,
    appVersion?: string,
  ) =>
    apiClient.post('/notifications/push-token', {
      expo_push_token: token,
      device_platform: platform,
      device_model: model,
      app_version: appVersion,
    }),

  deactivatePushToken: (token: string) =>
    apiClient.delete('/notifications/push-token', { data: { expo_push_token: token } }),
};
