import React from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import {
  useNotifications,
  useMarkRead,
  useMarkAllRead,
  useDeleteNotification,
} from '../../hooks/queries/useNotifications';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatRelativeTime } from '../../utils/formatting';
import type { Notification } from '../../types/models';

const TYPE_ICONS: Record<string, string> = {
  price_alert: '💰',
  community: '💬',
  system: 'ℹ️',
  announcement: '📢',
};

export default function NotificationsScreen() {
  const navigation = useNavigation<any>();
  const { data, isLoading, refetch, isRefetching } = useNotifications();
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();
  const deleteNotif = useDeleteNotification();

  const notifications = data?.data?.items ?? [];

  const handlePress = (n: Notification) => {
    if (!n.is_read) {
      markRead.mutate(n.id);
    }
    // Deep link based on type
    if (n.notification_type === 'price_alert' && n.data?.commodity_id) {
      navigation.navigate('Prices', {
        screen: 'CommodityDetail',
        params: { commodityId: n.data.commodity_id, commodityName: n.data.commodity_name ?? '' },
      });
    } else if (n.notification_type === 'community' && n.data?.post_id) {
      navigation.navigate('More', {
        screen: 'Community',
        params: { screen: 'PostDetail', params: { postId: n.data.post_id } },
      });
    }
  };

  const renderItem = ({ item }: { item: Notification }) => (
    <TouchableOpacity
      style={[styles.notifRow, !item.is_read && styles.unread]}
      onPress={() => handlePress(item)}
      activeOpacity={0.8}
    >
      <Text style={styles.icon}>{TYPE_ICONS[item.notification_type] ?? '🔔'}</Text>
      <View style={styles.content}>
        <Text style={[styles.title, !item.is_read && styles.titleBold]}>{item.title}</Text>
        <Text style={styles.message} numberOfLines={2}>{item.message}</Text>
        <Text style={styles.time}>{formatRelativeTime(item.created_at)}</Text>
      </View>
      <TouchableOpacity onPress={() => deleteNotif.mutate(item.id)} style={styles.deleteBtn}>
        <Text style={styles.deleteText}>✕</Text>
      </TouchableOpacity>
    </TouchableOpacity>
  );

  if (isLoading) return <LoadingSpinner fullScreen />;

  return (
    <View style={styles.container}>
      {notifications.length > 0 && (
        <TouchableOpacity style={styles.markAllBtn} onPress={() => markAllRead.mutate()}>
          <Text style={styles.markAllText}>Mark All Read</Text>
        </TouchableOpacity>
      )}
      <FlatList
        data={notifications}
        keyExtractor={n => n.id}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} />}
        ListEmptyComponent={<EmptyState icon="🔔" message="No notifications" />}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  markAllBtn: {
    padding: spacing[3],
    alignItems: 'flex-end',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.background,
  },
  markAllText: { color: colors.primary[600], fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium },
  notifRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: spacing[4],
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  unread: { backgroundColor: colors.primary[50] },
  icon: { fontSize: 20, marginRight: spacing[3] },
  content: { flex: 1 },
  title: { fontSize: typography.fontSize.sm, color: colors.text.primary, marginBottom: 2 },
  titleBold: { fontWeight: typography.fontWeight.semibold },
  message: { fontSize: typography.fontSize.xs, color: colors.text.secondary, marginBottom: 4 },
  time: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  deleteBtn: { padding: spacing[1] },
  deleteText: { color: colors.text.secondary, fontSize: 14 },
});
