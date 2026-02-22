import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  Modal,
  FlatList,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { commoditiesApi } from '../../api/commodities';
import type { Commodity } from '../../types/models';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import LoadingSpinner from '../ui/LoadingSpinner';

interface CommodityPickerProps {
  selectedId?: string;
  onChange: (commodityId: string, commodity: Commodity) => void;
  placeholder?: string;
}

export default function CommodityPicker({
  selectedId,
  onChange,
  placeholder = 'Select commodity...',
}: CommodityPickerProps) {
  const [visible, setVisible] = useState(false);
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['commodities', 'withPrices', 1, undefined],
    queryFn: () => commoditiesApi.getCommoditiesWithPrices(1, 100),
    staleTime: 5 * 60 * 1000,
  });

  const allCommodities: Commodity[] = data?.data?.commodities ?? [];

  const filtered = useMemo(() => {
    if (!search.trim()) return allCommodities;
    const q = search.toLowerCase();
    return allCommodities.filter(
      c =>
        c.name.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q),
    );
  }, [allCommodities, search]);

  const selected = allCommodities.find(c => c.id === selectedId);

  const handleSelect = (commodity: Commodity) => {
    onChange(commodity.id, commodity);
    setVisible(false);
    setSearch('');
  };

  return (
    <>
      <TouchableOpacity
        style={styles.trigger}
        onPress={() => setVisible(true)}
        activeOpacity={0.7}
      >
        {selected ? (
          <View>
            <Text style={styles.selectedName}>{selected.name}</Text>
            <Text style={styles.selectedCategory}>{selected.category}</Text>
          </View>
        ) : (
          <Text style={styles.placeholder}>{placeholder}</Text>
        )}
        <Text style={styles.chevron}>▼</Text>
      </TouchableOpacity>

      <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
        <SafeAreaView style={styles.modal}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Select Commodity</Text>
            <TouchableOpacity onPress={() => { setVisible(false); setSearch(''); }}>
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.searchContainer}>
            <TextInput
              style={styles.searchInput}
              placeholder="Search by name or category..."
              placeholderTextColor={colors.text.disabled}
              value={search}
              onChangeText={setSearch}
              autoFocus
              clearButtonMode="while-editing"
            />
          </View>

          {isLoading ? (
            <LoadingSpinner fullScreen />
          ) : (
            <FlatList
              data={filtered}
              keyExtractor={item => item.id}
              keyboardShouldPersistTaps="handled"
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.item,
                    item.id === selectedId && styles.itemSelected,
                  ]}
                  onPress={() => handleSelect(item)}
                  activeOpacity={0.7}
                >
                  <Text
                    style={[
                      styles.itemName,
                      item.id === selectedId && styles.itemNameSelected,
                    ]}
                  >
                    {item.name}
                  </Text>
                  <Text style={styles.itemCategory}>{item.category}</Text>
                </TouchableOpacity>
              )}
              ListEmptyComponent={
                <View style={styles.empty}>
                  <Text style={styles.emptyText}>No commodities found</Text>
                </View>
              }
            />
          )}
        </SafeAreaView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    backgroundColor: colors.background,
    minHeight: 48,
  },
  placeholder: {
    fontSize: typography.fontSize.base,
    color: colors.text.disabled,
    flex: 1,
  },
  selectedName: {
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
    fontWeight: typography.fontWeight.medium,
  },
  selectedCategory: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
    marginTop: 2,
  },
  chevron: {
    fontSize: 10,
    color: colors.text.secondary,
    marginLeft: spacing[2],
  },
  modal: {
    flex: 1,
    backgroundColor: colors.background,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  modalTitle: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
  },
  cancelText: {
    fontSize: typography.fontSize.base,
    color: colors.primary[600],
  },
  searchContainer: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  searchInput: {
    height: 40,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: spacing[3],
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
    backgroundColor: colors.surface,
  },
  item: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  itemSelected: {
    backgroundColor: colors.primary[50],
  },
  itemName: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.primary,
    marginBottom: 2,
  },
  itemNameSelected: {
    color: colors.primary[700],
  },
  itemCategory: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
  },
  empty: {
    padding: spacing[8],
    alignItems: 'center',
  },
  emptyText: {
    fontSize: typography.fontSize.base,
    color: colors.text.secondary,
  },
});
