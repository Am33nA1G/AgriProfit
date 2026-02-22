import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useAddSale } from '../../hooks/queries/useSales';
import CommodityPicker from '../../components/forms/CommodityPicker';
import Button from '../../components/ui/Button';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import type { Commodity } from '../../types/models';

const UNITS = ['quintal', 'kg', 'ton'] as const;
type Unit = (typeof UNITS)[number];

export default function AddSaleScreen() {
  const navigation = useNavigation();
  const { mutate: addSale, isPending } = useAddSale();

  const [commodityId, setCommodityId] = useState<string | undefined>();
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState<Unit>('quintal');
  const [salePrice, setSalePrice] = useState('');
  const [buyerName, setBuyerName] = useState('');

  const today = new Date().toISOString().split('T')[0];

  const handleSave = () => {
    if (!commodityId) {
      Alert.alert('Validation Error', 'Please select a commodity.');
      return;
    }
    const qty = parseFloat(quantity);
    if (!quantity || isNaN(qty) || qty <= 0) {
      Alert.alert('Validation Error', 'Please enter a valid quantity greater than 0.');
      return;
    }
    const price = parseFloat(salePrice);
    if (!salePrice || isNaN(price) || price <= 0) {
      Alert.alert('Validation Error', 'Please enter a valid sale price greater than 0.');
      return;
    }

    addSale(
      {
        commodity_id: commodityId,
        quantity: qty,
        unit,
        sale_price: price,
        buyer_name: buyerName.trim() || undefined,
        sale_date: today,
      },
      {
        onSuccess: () => {
          navigation.goBack();
        },
        onError: () => {
          Alert.alert('Error', 'Failed to record sale. Please try again.');
        },
      },
    );
  };

  return (
    <Screen style={styles.screen}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Commodity */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Commodity *</Text>
            <CommodityPicker
              selectedId={commodityId}
              onChange={(id: string, _commodity: Commodity) => setCommodityId(id)}
              placeholder="Select commodity..."
            />
          </View>

          {/* Quantity */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Quantity *</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter quantity"
              placeholderTextColor={colors.text.disabled}
              value={quantity}
              onChangeText={setQuantity}
              keyboardType="numeric"
              returnKeyType="next"
            />
          </View>

          {/* Unit */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Unit</Text>
            <View style={styles.unitRow}>
              {UNITS.map(u => (
                <TouchableOpacity
                  key={u}
                  style={[styles.unitChip, unit === u && styles.unitChipSelected]}
                  onPress={() => setUnit(u)}
                  activeOpacity={0.7}
                >
                  <Text
                    style={[
                      styles.unitChipText,
                      unit === u && styles.unitChipTextSelected,
                    ]}
                  >
                    {u}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Sale Price */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Sale Price (per unit, INR) *</Text>
            <View style={styles.priceInputWrapper}>
              <Text style={styles.currencySymbol}>₹</Text>
              <TextInput
                style={styles.priceInput}
                placeholder="e.g. 2500"
                placeholderTextColor={colors.text.disabled}
                value={salePrice}
                onChangeText={setSalePrice}
                keyboardType="numeric"
                returnKeyType="next"
              />
            </View>
          </View>

          {/* Buyer Name (optional) */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Buyer Name (optional)</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter buyer name"
              placeholderTextColor={colors.text.disabled}
              value={buyerName}
              onChangeText={setBuyerName}
              returnKeyType="done"
              autoCapitalize="words"
            />
          </View>

          {/* Date (read-only) */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Sale Date</Text>
            <View style={styles.dateDisplay}>
              <Text style={styles.dateText}>{today}</Text>
              <Text style={styles.dateHint}>(Today)</Text>
            </View>
          </View>

          <Button
            title="Record Sale"
            onPress={handleSave}
            loading={isPending}
            style={styles.saveButton}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    backgroundColor: colors.background,
  },
  flex: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing[4],
    paddingBottom: spacing[10],
  },
  fieldGroup: {
    marginBottom: spacing[5],
  },
  label: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.secondary,
    marginBottom: spacing[2],
  },
  input: {
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
  unitRow: {
    flexDirection: 'row',
    gap: spacing[2],
  },
  unitChip: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: 8,
    paddingVertical: spacing[3],
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  unitChipSelected: {
    borderColor: colors.primary[600],
    backgroundColor: colors.primary[50],
  },
  unitChipText: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.secondary,
  },
  unitChipTextSelected: {
    color: colors.primary[700],
  },
  priceInputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    backgroundColor: colors.background,
    minHeight: 48,
  },
  currencySymbol: {
    paddingHorizontal: spacing[3],
    fontSize: typography.fontSize.lg,
    color: colors.text.secondary,
    fontWeight: typography.fontWeight.medium,
  },
  priceInput: {
    flex: 1,
    paddingVertical: spacing[3],
    paddingRight: spacing[3],
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
  },
  dateDisplay: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    backgroundColor: colors.surface,
    minHeight: 48,
  },
  dateText: {
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
    fontWeight: typography.fontWeight.medium,
  },
  dateHint: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
  saveButton: {
    marginTop: spacing[4],
  },
});
