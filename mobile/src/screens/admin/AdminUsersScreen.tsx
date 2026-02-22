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
import { useAdminUsers } from '../../hooks/queries/useAdmin';
import { adminApi } from '../../api/admin';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import type { User } from '../../types/models';

export default function AdminUsersScreen() {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const { data, isLoading, refetch, isRefetching } = useAdminUsers(debouncedSearch || undefined);

  const users = data?.data ?? [];

  const handleSearchChange = (text: string) => {
    setSearch(text);
    clearTimeout((handleSearchChange as any)._timeout);
    (handleSearchChange as any)._timeout = setTimeout(() => setDebouncedSearch(text), 400);
  };

  const handleBan = (user: User) => {
    Alert.alert(
      'Ban User',
      `Ban ${user.name ?? user.phone}? They will lose access to the platform.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Ban',
          style: 'destructive',
          onPress: async () => {
            try {
              await adminApi.banUser(user.id);
              Alert.alert('Success', 'User has been banned.');
              refetch();
            } catch {
              Alert.alert('Error', 'Failed to ban user.');
            }
          },
        },
      ],
    );
  };

  const renderItem = ({ item }: { item: User }) => (
    <View style={styles.userCard}>
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>
          {(item.name ?? item.phone ?? '?')[0].toUpperCase()}
        </Text>
      </View>
      <View style={styles.userInfo}>
        <Text style={styles.userName}>{item.name ?? 'Unnamed User'}</Text>
        <Text style={styles.userPhone}>{item.phone}</Text>
        {item.state && (
          <Text style={styles.userLocation}>{item.district ? `${item.district}, ` : ''}{item.state}</Text>
        )}
      </View>
      <View style={styles.userActions}>
        <View style={[styles.roleBadge, item.role === 'admin' ? styles.roleAdmin : styles.roleUser]}>
          <Text style={styles.roleText}>{item.role ?? 'user'}</Text>
        </View>
        {item.role !== 'admin' && (
          <TouchableOpacity style={styles.banBtn} onPress={() => handleBan(item)}>
            <Text style={styles.banText}>Ban</Text>
          </TouchableOpacity>
        )}
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
          placeholder="Search users..."
          placeholderTextColor={colors.text.secondary}
          returnKeyType="search"
        />
      </View>
      <Text style={styles.countLabel}>{users.length} users found</Text>
      <FlatList
        data={users}
        keyExtractor={u => u.id}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} />}
        ListEmptyComponent={<EmptyState icon="👥" message="No users found" />}
        contentContainerStyle={users.length === 0 ? { flex: 1 } : { padding: spacing[3] }}
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
  countLabel: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  userCard: {
    backgroundColor: colors.background,
    borderRadius: 12,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary[100],
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing[3],
  },
  avatarText: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.primary[700] },
  userInfo: { flex: 1 },
  userName: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, color: colors.text.primary },
  userPhone: { fontSize: typography.fontSize.xs, color: colors.text.secondary, marginTop: 2 },
  userLocation: { fontSize: typography.fontSize.xs, color: colors.text.secondary, marginTop: 2 },
  userActions: { alignItems: 'flex-end', gap: spacing[2] },
  roleBadge: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: 4,
  },
  roleAdmin: { backgroundColor: '#fef3c7' },
  roleUser: { backgroundColor: '#f3f4f6' },
  roleText: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.medium, color: colors.text.secondary },
  banBtn: {
    paddingHorizontal: spacing[2],
    paddingVertical: 4,
    backgroundColor: '#fee2e2',
    borderRadius: 6,
  },
  banText: { fontSize: typography.fontSize.xs, color: colors.error, fontWeight: typography.fontWeight.medium },
});
