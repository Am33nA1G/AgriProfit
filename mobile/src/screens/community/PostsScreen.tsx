import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { CommunityStackParamList } from '../../types/navigation';
import { usePosts } from '../../hooks/queries/useCommunity';
import { useAuthStore } from '../../store/authStore';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatRelativeTime } from '../../utils/formatting';
import type { CommunityPost } from '../../types/models';

type Props = NativeStackScreenProps<CommunityStackParamList, 'Posts'>;

const FILTERS = ['All', 'My District', 'Questions', 'Tips', 'Alerts'];
const TYPE_MAP: Record<string, string> = {
  Questions: 'question',
  Tips: 'tip',
  Alerts: 'alert',
};

const TYPE_COLORS: Record<string, string> = {
  discussion: colors.primary[600],
  question: '#7c3aed',
  tip: '#0891b2',
  alert: colors.error,
};

export default function PostsScreen({ navigation }: Props) {
  const user = useAuthStore(s => s.user);
  const [filter, setFilter] = useState('All');
  const [page, setPage] = useState(1);

  const type = TYPE_MAP[filter];
  const district = filter === 'My District' ? user?.district ?? undefined : undefined;

  const { data, isLoading, refetch, isRefetching } = usePosts(page, type, district);
  const posts = data?.data?.items ?? [];

  const handleRefresh = async () => { setPage(1); await refetch(); };

  const renderItem = ({ item }: { item: CommunityPost }) => (
    <TouchableOpacity
      style={styles.postCard}
      onPress={() => navigation.navigate('PostDetail', { postId: item.id })}
      activeOpacity={0.8}
    >
      <View style={styles.postHeader}>
        <Text
          style={[styles.typeBadge, { backgroundColor: TYPE_COLORS[item.post_type] ?? colors.gray[500] }]}
        >
          {item.post_type}
        </Text>
        <Text style={styles.timestamp}>{formatRelativeTime(item.created_at)}</Text>
      </View>
      <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
      <Text style={styles.author}>by {item.author_name}</Text>
      <View style={styles.stats}>
        <Text style={styles.stat}>👍 {item.likes_count}</Text>
        <Text style={styles.stat}>💬 {item.replies_count}</Text>
      </View>
    </TouchableOpacity>
  );

  if (isLoading) return <LoadingSpinner fullScreen />;

  return (
    <View style={styles.container}>
      {/* Filter tabs */}
      <FlatList
        data={FILTERS}
        horizontal
        showsHorizontalScrollIndicator={false}
        keyExtractor={f => f}
        contentContainerStyle={styles.filterList}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.filterChip, filter === item && styles.filterChipActive]}
            onPress={() => { setFilter(item); setPage(1); }}
          >
            <Text style={[styles.filterText, filter === item && styles.filterTextActive]}>
              {item}
            </Text>
          </TouchableOpacity>
        )}
      />

      <FlatList
        data={posts}
        keyExtractor={p => p.id}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={handleRefresh} />}
        onEndReached={() => {
          if (data?.data && (data.data.skip + data.data.limit) < data.data.total) setPage(p => p + 1);
        }}
        onEndReachedThreshold={0.3}
        ListEmptyComponent={<EmptyState icon="💬" message="No posts yet. Be the first!" />}
      />

      {/* FAB */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('CreatePost')}
      >
        <Text style={styles.fabText}>＋</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  filterList: { paddingHorizontal: spacing[4], paddingVertical: spacing[2] },
  filterChip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    marginRight: spacing[2],
    backgroundColor: colors.background,
  },
  filterChipActive: { backgroundColor: colors.primary[600], borderColor: colors.primary[600] },
  filterText: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  filterTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
  postCard: {
    backgroundColor: colors.background,
    marginHorizontal: spacing[4],
    marginBottom: spacing[2],
    borderRadius: 12,
    padding: spacing[4],
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  postHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing[2],
  },
  typeBadge: {
    color: '#fff',
    fontSize: 10,
    fontWeight: typography.fontWeight.bold,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: 4,
    textTransform: 'uppercase',
  },
  timestamp: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  title: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
    marginBottom: spacing[1],
  },
  author: { fontSize: typography.fontSize.xs, color: colors.text.secondary, marginBottom: spacing[2] },
  stats: { flexDirection: 'row', gap: spacing[3] },
  stat: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  fab: {
    position: 'absolute',
    bottom: spacing[6],
    right: spacing[6],
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.primary[600],
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  fabText: { color: '#fff', fontSize: 24, fontWeight: typography.fontWeight.bold },
});
