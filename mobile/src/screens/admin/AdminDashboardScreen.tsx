import React from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AdminStackParamList } from '../../types/navigation';
import { useAdminStats } from '../../hooks/queries/useAdmin';
import Card from '../../components/ui/Card';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatDate } from '../../utils/formatting';

type Props = NativeStackScreenProps<AdminStackParamList, 'AdminDashboard'>;

export default function AdminDashboardScreen({ navigation }: Props) {
  const { data, isLoading } = useAdminStats();
  const stats = data?.data;

  if (isLoading) return <LoadingSpinner fullScreen />;

  const statCards = [
    { label: 'Total Users', value: stats?.total_users ?? '—', icon: '👥' },
    { label: 'Total Posts', value: stats?.total_posts ?? '—', icon: '📝' },
    { label: 'Active Commodities', value: stats?.active_commodities ?? '—', icon: '🌾' },
    { label: 'Last Sync', value: stats?.last_sync ? formatDate(stats.last_sync) : '—', icon: '🔄' },
  ];

  const actions = [
    { label: 'Broadcast Alert', screen: 'Broadcast' as const, icon: '📢' },
    { label: 'Manage Users', screen: 'AdminUsers' as const, icon: '👥' },
    { label: 'Manage Posts', screen: 'AdminPosts' as const, icon: '📝' },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Admin Dashboard</Text>

      <View style={styles.statsGrid}>
        {statCards.map(({ label, value, icon }) => (
          <Card key={label} style={styles.statCard}>
            <Text style={styles.statIcon}>{icon}</Text>
            <Text style={styles.statValue}>{String(value)}</Text>
            <Text style={styles.statLabel}>{label}</Text>
          </Card>
        ))}
      </View>

      <Text style={styles.sectionTitle}>Actions</Text>
      {actions.map(({ label, screen, icon }) => (
        <TouchableOpacity
          key={screen}
          style={styles.actionRow}
          onPress={() => navigation.navigate(screen)}
        >
          <Text style={styles.actionIcon}>{icon}</Text>
          <Text style={styles.actionLabel}>{label}</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing[4] },
  title: { fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.text.primary, marginBottom: spacing[4] },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3], marginBottom: spacing[6] },
  statCard: { width: '47%', alignItems: 'center', padding: spacing[4] },
  statIcon: { fontSize: 28, marginBottom: spacing[2] },
  statValue: { fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.bold, color: colors.text.primary },
  statLabel: { fontSize: typography.fontSize.xs, color: colors.text.secondary, textAlign: 'center', marginTop: 4 },
  sectionTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.text.primary, marginBottom: spacing[3] },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    borderRadius: 12,
    padding: spacing[4],
    marginBottom: spacing[2],
    borderWidth: 1,
    borderColor: colors.border,
  },
  actionIcon: { fontSize: 20, marginRight: spacing[3] },
  actionLabel: { flex: 1, fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.medium, color: colors.text.primary },
  chevron: { fontSize: 20, color: colors.text.secondary },
});
