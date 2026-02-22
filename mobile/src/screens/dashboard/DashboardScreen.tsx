import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  FlatList,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useAuthStore } from '../../store/authStore';
import { useQuery } from '@tanstack/react-query';
import { queryClient } from '../../api/queryClient';
import apiClient from '../../api/client';
import Card from '../../components/ui/Card';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatPrice } from '../../utils/formatting';

interface TopMover {
  commodity: string;
  price: number;
  change_percent: number;
}

export default function DashboardScreen() {
  const user = useAuthStore(s => s.user);
  const navigation = useNavigation<any>();

  const { data: topMovers, isLoading, refetch } = useQuery({
    queryKey: ['topMovers'],
    queryFn: () => apiClient.get<{ gainers: TopMover[]; losers: TopMover[] }>('/prices/top-movers'),
    staleTime: 5 * 60 * 1000,
  });

  const [refreshing, setRefreshing] = React.useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await queryClient.invalidateQueries();
    setRefreshing(false);
  };

  const quickActions = [
    { icon: '📈', label: 'Check Prices', screen: 'Prices' },
    { icon: '🚛', label: 'Calculate Transport', screen: 'Transport' },
    { icon: '📦', label: 'View Inventory', screen: 'More', params: { screen: 'Inventory' } },
  ];

  return (
    <Screen style={styles.screen}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.greeting}>Hello, {user?.name ?? 'Farmer'} 👋</Text>
          <Text style={styles.subtitle}>What would you like to do today?</Text>
        </View>

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          {quickActions.map(action => (
            <TouchableOpacity
              key={action.label}
              style={styles.actionCard}
              onPress={() => navigation.navigate(action.screen, action.params)}
            >
              <Text style={styles.actionIcon}>{action.icon}</Text>
              <Text style={styles.actionLabel}>{action.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Top Movers */}
        {topMovers?.data && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>📊 Top Movers</Text>

            <Text style={styles.subsectionTitle}>🟢 Gainers</Text>
            <FlatList
              data={topMovers.data.gainers?.slice(0, 5) ?? []}
              horizontal
              showsHorizontalScrollIndicator={false}
              keyExtractor={item => item.commodity}
              renderItem={({ item }) => (
                <Card style={styles.moverCard}>
                  <Text style={styles.moverName} numberOfLines={1}>{item.commodity}</Text>
                  <Text style={styles.moverPrice}>{formatPrice(item.price)}</Text>
                  <Text style={[styles.moverChange, { color: colors.priceUp }]}>
                    ↑ {item.change_percent?.toFixed(1)}%
                  </Text>
                </Card>
              )}
            />

            <Text style={[styles.subsectionTitle, { marginTop: spacing[3] }]}>🔴 Losers</Text>
            <FlatList
              data={topMovers.data.losers?.slice(0, 5) ?? []}
              horizontal
              showsHorizontalScrollIndicator={false}
              keyExtractor={item => item.commodity}
              renderItem={({ item }) => (
                <Card style={styles.moverCard}>
                  <Text style={styles.moverName} numberOfLines={1}>{item.commodity}</Text>
                  <Text style={styles.moverPrice}>{formatPrice(item.price)}</Text>
                  <Text style={[styles.moverChange, { color: colors.priceDown }]}>
                    ↓ {Math.abs(item.change_percent)?.toFixed(1)}%
                  </Text>
                </Card>
              )}
            />
          </View>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: colors.surface },
  header: {
    paddingVertical: spacing[4],
    paddingHorizontal: spacing[4],
  },
  greeting: {
    fontSize: typography.fontSize['2xl'],
    fontWeight: typography.fontWeight.bold,
    color: colors.text.primary,
    marginBottom: spacing[1],
  },
  subtitle: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
  quickActions: {
    flexDirection: 'row',
    paddingHorizontal: spacing[4],
    gap: spacing[3],
    marginBottom: spacing[4],
  },
  actionCard: {
    flex: 1,
    backgroundColor: colors.background,
    borderRadius: 12,
    padding: spacing[3],
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 2,
    borderWidth: 1,
    borderColor: colors.border,
  },
  actionIcon: { fontSize: 28, marginBottom: spacing[1] },
  actionLabel: {
    fontSize: typography.fontSize.xs,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.primary,
    textAlign: 'center',
  },
  section: {
    paddingHorizontal: spacing[4],
    marginBottom: spacing[6],
  },
  sectionTitle: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
    marginBottom: spacing[3],
  },
  subsectionTitle: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.secondary,
    marginBottom: spacing[2],
  },
  moverCard: {
    width: 120,
    marginRight: spacing[2],
    padding: spacing[3],
  },
  moverName: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
    marginBottom: spacing[1],
  },
  moverPrice: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
    marginBottom: spacing[1],
  },
  moverChange: {
    fontSize: typography.fontSize.xs,
    fontWeight: typography.fontWeight.medium,
  },
});
