import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  TextInput,
  Alert,
  RefreshControl,
} from 'react-native';
import { useAdminPosts, useAdminDeletePost } from '../../hooks/queries/useAdmin';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatRelativeTime } from '../../utils/formatting';
import type { CommunityPost } from '../../types/models';

export default function AdminPostsScreen() {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const { data, isLoading, refetch, isRefetching } = useAdminPosts(debouncedSearch || undefined);
  const deletePost = useAdminDeletePost();

  const posts = data?.data ?? [];

  const handleSearchChange = (text: string) => {
    setSearch(text);
    // Simple debounce via timeout ref pattern
    clearTimeout((handleSearchChange as any)._timeout);
    (handleSearchChange as any)._timeout = setTimeout(() => setDebouncedSearch(text), 400);
  };

  const handleDelete = (post: CommunityPost) => {
    Alert.alert(
      'Delete Post',
      `Delete "${post.title}"? This cannot be undone.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            deletePost.mutate(post.id, {
              onError: () => Alert.alert('Error', 'Failed to delete post.'),
            });
          },
        },
      ],
    );
  };

  const renderItem = ({ item }: { item: CommunityPost }) => (
    <View style={styles.postCard}>
      <View style={styles.postHeader}>
        <View style={[styles.typeBadge, styles[`badge_${item.post_type}` as keyof typeof styles] ?? styles.badge_default]}>
          <Text style={styles.typeText}>{item.post_type}</Text>
        </View>
        <Text style={styles.postDate}>{formatRelativeTime(item.created_at)}</Text>
      </View>
      <Text style={styles.postTitle} numberOfLines={2}>{item.title}</Text>
      <Text style={styles.postContent} numberOfLines={2}>{item.content}</Text>
      <View style={styles.postFooter}>
        <Text style={styles.postMeta}>
          👤 {item.author_name ?? 'Unknown'} · 👍 {item.upvotes ?? 0} · 💬 {item.replies_count ?? 0}
        </Text>
        <TouchableOpacity style={styles.deleteBtn} onPress={() => handleDelete(item)}>
          <Text style={styles.deleteText}>🗑 Delete</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  if (isLoading) return <LoadingSpinner fullScreen />;

  return (
    <View style={styles.container}>
      <View style={styles.searchBar}>
        <TextInput
          style={styles.searchInput}
          value={search}
          onChangeText={handleSearchChange}
          placeholder="Search posts..."
          placeholderTextColor={colors.text.secondary}
          returnKeyType="search"
        />
      </View>
      <FlatList
        data={posts}
        keyExtractor={p => p.id}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} />}
        ListEmptyComponent={<EmptyState icon="📝" message="No posts found" />}
        contentContainerStyle={posts.length === 0 ? { flex: 1 } : { padding: spacing[3] }}
        ItemSeparatorComponent={() => <View style={{ height: spacing[2] }} />}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  searchBar: {
    padding: spacing[3],
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  searchInput: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    fontSize: typography.fontSize.sm,
    color: colors.text.primary,
  },
  postCard: {
    backgroundColor: colors.background,
    borderRadius: 12,
    padding: spacing[4],
    borderWidth: 1,
    borderColor: colors.border,
  },
  postHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing[2] },
  typeBadge: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: 4,
    marginRight: spacing[2],
  },
  badge_question: { backgroundColor: '#dbeafe' },
  badge_tip: { backgroundColor: '#dcfce7' },
  badge_alert: { backgroundColor: '#fee2e2' },
  badge_general: { backgroundColor: '#f3f4f6' },
  badge_default: { backgroundColor: '#f3f4f6' },
  typeText: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.medium, color: colors.text.secondary },
  postDate: { marginLeft: 'auto', fontSize: typography.fontSize.xs, color: colors.text.secondary },
  postTitle: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, color: colors.text.primary, marginBottom: 4 },
  postContent: { fontSize: typography.fontSize.xs, color: colors.text.secondary, marginBottom: spacing[3] },
  postFooter: { flexDirection: 'row', alignItems: 'center' },
  postMeta: { flex: 1, fontSize: typography.fontSize.xs, color: colors.text.secondary },
  deleteBtn: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    backgroundColor: '#fee2e2',
    borderRadius: 6,
  },
  deleteText: { fontSize: typography.fontSize.xs, color: colors.error, fontWeight: typography.fontWeight.medium },
});
