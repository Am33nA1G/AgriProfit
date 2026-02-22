import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useTransportCompare } from '../../hooks/queries/useTransport';
import StatePicker from '../../components/forms/StatePicker';
import DistrictPicker from '../../components/forms/DistrictPicker';
import CommodityPicker from '../../components/forms/CommodityPicker';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import EmptyState from '../../components/ui/EmptyState';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatPrice } from '../../utils/formatting';
import type { TransportCalculation, Commodity } from '../../types/models';

export default function TransportScreen() {
  const [selectedState, setSelectedState] = useState<string | undefined>();
  const [selectedDistrict, setSelectedDistrict] = useState<string | undefined>();
  const [selectedCommodityId, setSelectedCommodityId] = useState<string | undefined>();
  const [quantity, setQuantity] = useState('');

  const { mutate: compare, data: results, isPending, reset } = useTransportCompare();

  const handleStateChange = (state: string) => {
    setSelectedState(state);
    // Reset district when state changes
    setSelectedDistrict(undefined);
  };

  const handleCompare = () => {
    if (!selectedDistrict) {
      Alert.alert('Missing Info', 'Please select your district.');
      return;
    }
    if (!selectedCommodityId) {
      Alert.alert('Missing Info', 'Please select a commodity.');
      return;
    }
    const qty = parseFloat(quantity);
    if (!quantity || isNaN(qty) || qty <= 0) {
      Alert.alert('Invalid Quantity', 'Please enter a valid quantity greater than 0.');
      return;
    }
    compare({ origin: selectedDistrict, commodityId: selectedCommodityId, quantity: qty });
  };

  const sortedResults: TransportCalculation[] = results?.data
    ? [...results.data].sort((a, b) => b.net_profit - a.net_profit)
    : [];

  const renderResult = ({ item, index }: { item: TransportCalculation; index: number }) => {
    const isProfit = item.net_profit >= 0;
    return (
      <Card style={[styles.resultCard, index === 0 && styles.topResult]}>
        {index === 0 && (
          <View style={styles.bestBadge}>
            <Text style={styles.bestBadgeText}>Best Option</Text>
          </View>
        )}
        <View style={styles.resultHeader}>
          <View style={styles.resultLeft}>
            <Text style={styles.mandiName}>{item.mandi_name}</Text>
            <Text style={styles.mandiLocation}>
              {item.district}, {item.state}
            </Text>
          </View>
          <Text
            style={[
              styles.netProfit,
              isProfit ? styles.profitPositive : styles.profitNegative,
            ]}
          >
            {isProfit ? '+' : ''}{formatPrice(item.net_profit)}
          </Text>
        </View>

        <View style={styles.resultDetails}>
          <View style={styles.detailItem}>
            <Text style={styles.detailLabel}>Distance</Text>
            <Text style={styles.detailValue}>{item.distance_km.toFixed(0)} km</Text>
          </View>
          <View style={styles.detailItem}>
            <Text style={styles.detailLabel}>Transport</Text>
            <Text style={[styles.detailValue, styles.costRed]}>
              -{formatPrice(item.transport_cost)}
            </Text>
          </View>
          <View style={styles.detailItem}>
            <Text style={styles.detailLabel}>Mandi Price</Text>
            <Text style={styles.detailValue}>{formatPrice(item.commodity_price)}/q</Text>
          </View>
        </View>
      </Card>
    );
  };

  return (
    <Screen style={styles.screen}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}
      >
        <FlatList
          data={sortedResults}
          keyExtractor={item => item.mandi_id}
          renderItem={renderResult}
          ListHeaderComponent={
            <View style={styles.formContainer}>
              <Text style={styles.sectionTitle}>Your Location</Text>

              <Text style={styles.label}>State</Text>
              <StatePicker
                selectedState={selectedState}
                onChange={handleStateChange}
                placeholder="Select your state..."
              />

              <Text style={[styles.label, styles.labelSpacing]}>District</Text>
              <DistrictPicker
                selectedState={selectedState}
                selectedDistrict={selectedDistrict}
                onChange={setSelectedDistrict}
                placeholder={selectedState ? 'Select your district...' : 'Select state first'}
              />

              <Text style={[styles.sectionTitle, styles.sectionSpacing]}>Commodity</Text>

              <Text style={styles.label}>Commodity</Text>
              <CommodityPicker
                selectedId={selectedCommodityId}
                onChange={(id: string, _commodity: Commodity) => setSelectedCommodityId(id)}
                placeholder="Select commodity..."
              />

              <Text style={[styles.label, styles.labelSpacing]}>Quantity (quintals)</Text>
              <TextInput
                style={styles.quantityInput}
                placeholder="e.g. 10"
                placeholderTextColor={colors.text.disabled}
                value={quantity}
                onChangeText={setQuantity}
                keyboardType="numeric"
                returnKeyType="done"
              />

              <Button
                title={isPending ? 'Comparing...' : 'Compare Mandis'}
                onPress={handleCompare}
                loading={isPending}
                style={styles.compareButton}
              />

              {sortedResults.length > 0 && (
                <View style={styles.resultsHeader}>
                  <Text style={styles.resultsTitle}>
                    {sortedResults.length} Mandis Found
                  </Text>
                  <Text style={styles.resultsSubtitle}>Sorted by highest net profit</Text>
                </View>
              )}
            </View>
          }
          ListEmptyComponent={
            isPending ? (
              <View style={styles.loadingContainer}>
                <LoadingSpinner />
                <Text style={styles.loadingText}>Comparing mandis...</Text>
              </View>
            ) : results ? (
              <EmptyState
                icon="🏪"
                message="No mandis found for your location and commodity selection."
              />
            ) : null
          }
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        />
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    backgroundColor: colors.surface,
  },
  flex: {
    flex: 1,
  },
  listContent: {
    flexGrow: 1,
    paddingBottom: spacing[8],
  },
  formContainer: {
    padding: spacing[4],
    backgroundColor: colors.background,
    marginBottom: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  sectionTitle: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
    marginBottom: spacing[3],
  },
  sectionSpacing: {
    marginTop: spacing[4],
  },
  label: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.secondary,
    marginBottom: spacing[1],
  },
  labelSpacing: {
    marginTop: spacing[3],
  },
  quantityInput: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
    backgroundColor: colors.background,
    minHeight: 48,
  },
  compareButton: {
    marginTop: spacing[5],
  },
  resultsHeader: {
    marginTop: spacing[5],
    paddingTop: spacing[4],
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  resultsTitle: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
  },
  resultsSubtitle: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
    marginTop: spacing[1],
  },
  loadingContainer: {
    alignItems: 'center',
    paddingVertical: spacing[10],
    gap: spacing[3],
  },
  loadingText: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
  resultCard: {
    marginHorizontal: spacing[4],
    marginBottom: spacing[3],
  },
  topResult: {
    borderColor: colors.primary[400],
    borderWidth: 2,
  },
  bestBadge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.primary[600],
    borderRadius: 4,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    marginBottom: spacing[2],
  },
  bestBadgeText: {
    fontSize: typography.fontSize.xs,
    color: colors.text.inverse,
    fontWeight: typography.fontWeight.semibold,
  },
  resultHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: spacing[3],
  },
  resultLeft: {
    flex: 1,
    marginRight: spacing[2],
  },
  mandiName: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
    marginBottom: 2,
  },
  mandiLocation: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
  },
  netProfit: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
  },
  profitPositive: {
    color: colors.priceUp,
  },
  profitNegative: {
    color: colors.priceDown,
  },
  resultDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: spacing[3],
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  detailItem: {
    alignItems: 'center',
    flex: 1,
  },
  detailLabel: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
    marginBottom: 2,
  },
  detailValue: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.primary,
  },
  costRed: {
    color: colors.priceDown,
  },
});
