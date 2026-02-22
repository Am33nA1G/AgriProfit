import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { PricesStackParamList } from '../../types/navigation';
import { useCommodityDetail } from '../../hooks/queries/useCommodities';
import { useForecasts } from '../../hooks/queries/useForecasts';
import PriceChart from '../../components/charts/PriceChart';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import Card from '../../components/ui/Card';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatPrice, formatDate } from '../../utils/formatting';

type Props = NativeStackScreenProps<PricesStackParamList, 'CommodityDetail'>;

export default function CommodityDetailScreen({ route }: Props) {
  const { commodityId } = route.params;
  const [days, setDays] = useState<7 | 30>(30);

  const { data: detail, isLoading: detailLoading, refetch } = useCommodityDetail(commodityId);
  const { data: forecasts } = useForecasts(commodityId);

  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  if (detailLoading) return <LoadingSpinner fullScreen />;

  const commodity = detail?.data;
  const priceHistory: Array<{ date: string; price: number }> = commodity?.price_history ?? [];
  const mandis: Array<{ name: string; state: string; district: string; price: number; as_of: string }> =
    commodity?.top_mandis ?? [];
  const forecastList = forecasts?.data ?? [];

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />}
      showsVerticalScrollIndicator={false}
    >
      {/* Header */}
      <Card style={styles.headerCard}>
        <Text style={styles.categoryBadge}>{commodity?.category ?? ''}</Text>
        <Text style={styles.currentPrice}>
          {commodity?.current_price ? formatPrice(commodity.current_price) : '—'}
        </Text>
        {commodity?.price_changes?.['1d'] != null && (
          <Text
            style={[
              styles.priceChange,
              commodity.price_changes['1d'] > 0 ? styles.changeUp : styles.changeDown,
            ]}
          >
            {commodity.price_changes['1d'] > 0 ? '↑' : '↓'}
            {' '}{Math.abs(commodity.price_changes['1d']).toFixed(2)}% today
          </Text>
        )}
      </Card>

      {/* Price Chart */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Price History</Text>
          <View style={styles.dayToggle}>
            {([7, 30] as const).map(d => (
              <TouchableOpacity
                key={d}
                style={[styles.toggleBtn, days === d && styles.toggleBtnActive]}
                onPress={() => setDays(d)}
              >
                <Text style={[styles.toggleText, days === d && styles.toggleTextActive]}>
                  {d}d
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
        {detailLoading ? (
          <LoadingSpinner />
        ) : (
          <PriceChart priceHistory={priceHistory} days={days} />
        )}
      </View>

      {/* Mandi Prices */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Mandi Prices</Text>
        {mandis.slice(0, 10).map((mandi) => (
          <View key={`${mandi.name}-${mandi.as_of}`} style={styles.mandiRow}>
            <View style={styles.mandiLeft}>
              <Text style={styles.mandiName}>{mandi.name}</Text>
              <Text style={styles.mandiDistrict}>{mandi.district}, {mandi.state}</Text>
            </View>
            <View style={styles.mandiRight}>
              <Text style={styles.mandiPrice}>{formatPrice(mandi.price)}</Text>
              <Text style={styles.mandiDate}>{formatDate(mandi.as_of)}</Text>
            </View>
          </View>
        ))}
        {mandis.length === 0 && (
          <Text style={styles.empty}>No mandi data available</Text>
        )}
      </View>

      {/* Forecasts */}
      {forecastList.length > 0 && (
        <View style={[styles.section, styles.lastSection]}>
          <Text style={styles.sectionTitle}>Price Forecast</Text>
          {forecastList.map((f: any) => (
            <Card key={f.id} style={styles.forecastCard}>
              <Text style={styles.forecastType}>{formatDate(f.forecast_date)} Forecast</Text>
              <Text style={styles.forecastPrice}>{formatPrice(f.predicted_price)}</Text>
              <Text style={styles.forecastConf}>Confidence: {f.confidence_level != null ? Math.round(f.confidence_level * 100) : '—'}%</Text>
            </Card>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  headerCard: { margin: spacing[4], marginBottom: spacing[2], alignItems: 'center' },
  categoryBadge: {
    fontSize: typography.fontSize.sm,
    color: colors.primary[600],
    backgroundColor: colors.primary[50],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: 12,
    marginBottom: spacing[2],
  },
  currentPrice: {
    fontSize: typography.fontSize['3xl'],
    fontWeight: typography.fontWeight.bold,
    color: colors.text.primary,
  },
  priceChange: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    marginTop: spacing[1],
  },
  changeUp: { color: colors.priceUp },
  changeDown: { color: colors.priceDown },
  section: {
    backgroundColor: colors.background,
    marginHorizontal: spacing[4],
    marginBottom: spacing[3],
    borderRadius: 12,
    padding: spacing[4],
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 1,
    borderWidth: 1,
    borderColor: colors.border,
  },
  lastSection: { marginBottom: spacing[8] },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing[2],
  },
  sectionTitle: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
  },
  dayToggle: { flexDirection: 'row', gap: spacing[1] },
  toggleBtn: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  toggleBtnActive: { backgroundColor: colors.primary[600], borderColor: colors.primary[600] },
  toggleText: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  toggleTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
  mandiRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing[2],
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  mandiLeft: { flex: 1 },
  mandiRight: { alignItems: 'flex-end' },
  mandiName: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.text.primary },
  mandiDistrict: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  mandiPrice: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, color: colors.text.primary },
  mandiDate: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  empty: { fontSize: typography.fontSize.sm, color: colors.text.secondary, textAlign: 'center', paddingVertical: spacing[4] },
  forecastCard: { marginBottom: spacing[2] },
  forecastType: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  forecastPrice: { fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.bold, color: colors.text.primary },
  forecastConf: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
});
