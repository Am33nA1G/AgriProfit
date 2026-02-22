import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ScrollView,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { MoreStackParamList } from '../../types/navigation';
import { useSales, useSalesAnalytics } from '../../hooks/queries/useSales';
import Card from '../../components/ui/Card';
import EmptyState from '../../components/ui/EmptyState';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatPrice, formatDate } from '../../utils/formatting';
import type { SaleRecord } from '../../types/models';

type NavProp = NativeStackNavigationProp<MoreStackParamList>;

type TabType = 'history' | 'analytics';

interface CommodityAnalytic {
  commodity_name: string;
  total_quantity: number;
  total_revenue: number;
  sale_count: number;
  avg_price: number;
}

interface AnalyticsData {
  total_revenue: number;
  total_sales: number;
  avg_price: number;
  by_commodity?: CommodityAnalytic[];
}

function HistoryTab() {
  const navigation = useNavigation<NavProp>();
  const { data, isLoading, refetch } = useSales();
  const [refreshing, setRefreshing] = useState(false);

  const sales: SaleRecord[] = data?.data ?? [];

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  if (isLoading) return <LoadingSpinner fullScreen />;

  return (
    <View style={styles.tabContent}>
      <FlatList
        data={sales}
        keyExtractor={item => item.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        contentContainerStyle={styles.listContent}
        renderItem={({ item }) => (
          <Card style={styles.saleCard}>
            <View style={styles.saleHeader}>
              <Text style={styles.commodityName}>{item.commodity_name}</Text>
              <Text style={styles.totalAmount}>{formatPrice(item.total_amount)}</Text>
            </View>
            <View style={styles.saleMeta}>
              <Text style={styles.saleDetail}>
                {item.quantity} {item.unit} @ {formatPrice(item.sale_price)}/unit
              </Text>
              <Text style={styles.saleDate}>{formatDate(item.sale_date)}</Text>
            </View>
            {item.buyer_name && (
              <Text style={styles.buyerName}>Buyer: {item.buyer_name}</Text>
            )}
          </Card>
        )}
        ListEmptyComponent={
          <EmptyState
            icon="💰"
            message="No sales recorded yet"
            actionLabel="Record Sale"
            onAction={() => navigation.navigate('AddSale')}
          />
        }
        showsVerticalScrollIndicator={false}
      />

      {/* FAB */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('AddSale')}
        activeOpacity={0.85}
      >
        <Text style={styles.fabIcon}>+</Text>
      </TouchableOpacity>
    </View>
  );
}

function AnalyticsTab() {
  const { data, isLoading, refetch } = useSalesAnalytics();
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  if (isLoading) return <LoadingSpinner fullScreen />;

  const analytics = data?.data as AnalyticsData | undefined;

  return (
    <ScrollView
      style={styles.tabContent}
      contentContainerStyle={styles.analyticsContent}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
      }
      showsVerticalScrollIndicator={false}
    >
      {analytics ? (
        <>
          {/* Summary Cards */}
          <View style={styles.summaryRow}>
            <Card style={styles.summaryCard}>
              <Text style={styles.summaryValue}>
                {formatPrice(analytics.total_revenue ?? 0)}
              </Text>
              <Text style={styles.summaryLabel}>Total Revenue</Text>
            </Card>
            <Card style={styles.summaryCard}>
              <Text style={styles.summaryValue}>{analytics.total_sales ?? 0}</Text>
              <Text style={styles.summaryLabel}>Total Sales</Text>
            </Card>
          </View>

          {/* Average price */}
          {analytics.avg_price != null && (
            <Card style={styles.avgCard}>
              <Text style={styles.avgLabel}>Average Sale Price</Text>
              <Text style={styles.avgValue}>{formatPrice(analytics.avg_price)}</Text>
            </Card>
          )}

          {/* Per-commodity breakdown */}
          {analytics.by_commodity && analytics.by_commodity.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>By Commodity</Text>
              {analytics.by_commodity.map(c => (
                <Card key={c.commodity_name} style={styles.commodityAnalyticCard}>
                  <View style={styles.commodityAnalyticHeader}>
                    <Text style={styles.commodityAnalyticName}>
                      {c.commodity_name}
                    </Text>
                    <Text style={styles.commodityRevenue}>
                      {formatPrice(c.total_revenue)}
                    </Text>
                  </View>
                  <Text style={styles.commodityAnalyticDetail}>
                    {c.sale_count} sales • {c.total_quantity} units •{' '}
                    avg {formatPrice(c.avg_price)}
                  </Text>
                </Card>
              ))}
            </View>
          )}
        </>
      ) : (
        <EmptyState icon="📊" message="No analytics data available yet" />
      )}
    </ScrollView>
  );
}

export default function SalesScreen() {
  const [activeTab, setActiveTab] = useState<TabType>('history');

  return (
    <Screen style={styles.screen}>
      {/* Tabs */}
      <View style={styles.tabBar}>
        {(['history', 'analytics'] as TabType[]).map(tab => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, activeTab === tab && styles.tabActive]}
            onPress={() => setActiveTab(tab)}
            activeOpacity={0.7}
          >
            <Text
              style={[styles.tabText, activeTab === tab && styles.tabTextActive]}
            >
              {tab === 'history' ? 'History' : 'Analytics'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {activeTab === 'history' ? <HistoryTab /> : <AnalyticsTab />}
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    backgroundColor: colors.surface,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tab: {
    flex: 1,
    paddingVertical: spacing[3],
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: colors.primary[600],
  },
  tabText: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.secondary,
  },
  tabTextActive: {
    color: colors.primary[600],
    fontWeight: typography.fontWeight.semibold,
  },
  tabContent: {
    flex: 1,
  },
  listContent: {
    padding: spacing[4],
    paddingBottom: spacing[20],
    flexGrow: 1,
  },
  analyticsContent: {
    padding: spacing[4],
    paddingBottom: spacing[10],
  },
  saleCard: {
    marginBottom: spacing[3],
  },
  saleHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: spacing[2],
  },
  commodityName: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
    flex: 1,
    marginRight: spacing[2],
  },
  totalAmount: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary[700],
  },
  saleMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  saleDetail: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
  saleDate: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
  buyerName: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
    marginTop: spacing[1],
    fontStyle: 'italic',
  },
  fab: {
    position: 'absolute',
    right: spacing[5],
    bottom: spacing[8],
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary[600],
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
  fabIcon: {
    fontSize: 28,
    color: colors.text.inverse,
    lineHeight: 32,
    fontWeight: typography.fontWeight.normal,
  },
  summaryRow: {
    flexDirection: 'row',
    gap: spacing[3],
    marginBottom: spacing[3],
  },
  summaryCard: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing[4],
  },
  summaryValue: {
    fontSize: typography.fontSize.xl,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary[700],
    marginBottom: spacing[1],
  },
  summaryLabel: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
    textAlign: 'center',
  },
  avgCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing[4],
    paddingVertical: spacing[3],
  },
  avgLabel: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
  avgValue: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.text.primary,
  },
  section: {
    marginBottom: spacing[4],
  },
  sectionTitle: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
    marginBottom: spacing[3],
  },
  commodityAnalyticCard: {
    marginBottom: spacing[2],
  },
  commodityAnalyticHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing[1],
  },
  commodityAnalyticName: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.primary,
  },
  commodityRevenue: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary[700],
  },
  commodityAnalyticDetail: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
  },
});
