import api from '@/lib/api';

// Notification types
export type NotificationType =
    | 'PRICE_ALERT'
    | 'FORUM_REPLY'
    | 'NEW_POST'
    | 'SYSTEM'
    | 'WEATHER_ALERT'
    | 'MARKET_UPDATE';

export interface Notification {
    id: string;
    type: NotificationType;
    title: string;
    message: string;
    read: boolean;
    created_at: string;
    link?: string;
}

export interface NotificationsResponse {
    notifications: Notification[];
    unread_count: number;
}

export interface Activity {
    id: string;
    type: 'price' | 'post' | 'forecast';
    title: string;
    timestamp: string;
    detail?: string;
}

// Legacy backend response format
export interface NotificationResponse {
    id: string;
    user_id: string;
    title?: string;
    message: string;
    notification_type?: string;
    is_read: boolean;
    created_at: string;
    read_at?: string;
    related_id?: string;
}

// Transform backend response to frontend format
function transformNotification(n: NotificationResponse): Notification {
    return {
        id: n.id,
        type: mapNotificationType(n.notification_type),
        title: n.title || getDefaultTitle(n.notification_type),
        message: n.message,
        read: n.is_read,
        created_at: n.created_at,
        link: getNotificationLink(n)
    };
}

function mapNotificationType(type?: string): NotificationType {
    if (!type) return 'SYSTEM';
    const normalized = type.toUpperCase().replace(/-/g, '_');
    if (normalized.includes('PRICE')) return 'PRICE_ALERT';
    if (normalized.includes('REPLY') || normalized.includes('COMMENT')) return 'FORUM_REPLY';
    if (normalized.includes('POST')) return 'NEW_POST';
    if (normalized.includes('WEATHER')) return 'WEATHER_ALERT';
    if (normalized.includes('MARKET')) return 'MARKET_UPDATE';
    return 'SYSTEM';
}

function getDefaultTitle(type?: string): string {
    if (!type) return 'Notification';
    if (type.includes('price')) return 'Price Alert';
    if (type.includes('reply') || type.includes('comment')) return 'New Reply';
    if (type.includes('post')) return 'New Post';
    if (type.includes('weather')) return 'Weather Alert';
    if (type.includes('market')) return 'Market Update';
    return 'Notification';
}

function getNotificationLink(n: NotificationResponse): string | undefined {
    const type = n.notification_type?.toLowerCase() || '';
    if (type.includes('price') || type.includes('market')) return '/dashboard';
    if (type.includes('post') || type.includes('reply')) {
        return n.related_id ? `/community?post=${n.related_id}` : '/community';
    }
    return undefined;
}

export const notificationsService = {
    /**
     * Get notifications with pagination and filtering
     */
    async getNotifications(params?: {
        limit?: number;
        skip?: number;
        unread_only?: boolean;
        type?: string;
        startDate?: string;
        endDate?: string;
    }): Promise<NotificationsResponse> {
        try {
            const queryParams: Record<string, string | number | boolean> = {};
            if (params?.limit) queryParams.limit = params.limit;
            if (params?.skip) queryParams.skip = params.skip;
            if (params?.unread_only) queryParams.is_read = false;
            if (params?.type && params.type !== 'ALL') queryParams.notification_type = params.type;
            if (params?.startDate) queryParams.start_date = params.startDate;
            if (params?.endDate) queryParams.end_date = params.endDate;

            const response = await api.get('/notifications', { params: queryParams });
            const items = response.data.items || response.data || [];

            // Get unread count
            let unreadCount = 0;
            try {
                const countResponse = await api.get('/notifications/unread-count');
                unreadCount = countResponse.data.unread_count || 0;
            } catch {
                // Calculate from items if endpoint fails
                unreadCount = items.filter((n: NotificationResponse) => !n.is_read).length;
            }

            return {
                notifications: items.map(transformNotification),
                unread_count: unreadCount
            };
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
            return { notifications: [], unread_count: 0 };
        }
    },

    /**
     * Get unread notification count
     */
    async getUnreadCount(): Promise<number> {
        try {
            const response = await api.get('/notifications/unread-count');
            return response.data.unread_count || 0;
        } catch {
            return 0;
        }
    },

    /**
     * Mark a single notification as read
     */
    async markAsRead(notificationId: string): Promise<boolean> {
        try {
            await api.put(`/notifications/${notificationId}/read`);
            return true;
        } catch (error) {
            console.error('Failed to mark notification as read:', error);
            return false;
        }
    },

    /**
     * Mark all notifications as read
     */
    async markAllAsRead(): Promise<boolean> {
        try {
            await api.put('/notifications/read-all');
            return true;
        } catch (error) {
            console.error('Failed to mark all notifications as read:', error);
            return false;
        }
    },

    /**
     * Mark multiple notifications as read
     */
    async markNotificationsAsRead(ids: string[]): Promise<boolean> {
        try {
            // Processing in parallel as there might not be a bulk endpoint
            await Promise.all(ids.map(id => api.put(`/notifications/${id}/read`)));
            return true;
        } catch (error) {
            console.error('Failed to mark notifications as read:', error);
            return false;
        }
    },

    /**
     * Delete a notification
     */
    async deleteNotification(id: string): Promise<boolean> {
        try {
            await api.delete(`/notifications/${id}`);
            return true;
        } catch (error) {
            console.error('Failed to delete notification:', error);
            return false;
        }
    },

    /**
     * Delete multiple notifications
     */
    async deleteNotifications(ids: string[]): Promise<boolean> {
        try {
            await Promise.all(ids.map(id => api.delete(`/notifications/${id}`)));
            return true;
        } catch (error) {
            console.error('Failed to delete notifications:', error);
            return false;
        }
    },

    /**
     * Clear all notifications (delete all read notifications)
     */
    async clearAllNotifications(): Promise<boolean> {
        try {
            // Backend endpoint is /notifications/read (deletes all read notifications)
            await api.delete('/notifications/read');
            return true;
        } catch (error) {
            console.error('Failed to clear notifications:', error);
            return false;
        }
    },

    /**
     * Get recent activity for dashboard
     */
    async getRecentActivity(limit: number = 5): Promise<Activity[]> {
        try {
            const response = await api.get('/notifications', {
                params: { limit }
            });

            const notifications = response.data.items || response.data || [];

            return notifications.map((notification: NotificationResponse) => ({
                id: notification.id,
                type: getActivityType(notification.notification_type || ''),
                title: notification.title || notification.message || 'New update',
                timestamp: formatTimestamp(notification.created_at),
                detail: notification.message
            }));
        } catch (error) {
            console.error('Failed to fetch activity:', error);
            return [];
        }
    }
};

function getActivityType(notificationType: string): 'price' | 'post' | 'forecast' {
    if (notificationType?.includes('price')) return 'price';
    if (notificationType?.includes('forecast')) return 'forecast';
    if (notificationType?.includes('weather')) return 'forecast';
    return 'post';
}

function formatTimestamp(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} mins ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
    return `${Math.floor(diffMins / 1440)} days ago`;
}

/**
 * Format relative time for notifications
 */
export function formatRelativeTime(dateString: string): string {
    return formatTimestamp(dateString);
}
