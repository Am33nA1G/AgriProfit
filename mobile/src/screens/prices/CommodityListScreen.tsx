import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { PricesStackParamList } from '../../types/navigation';
import {
  useCommoditiesWithPrices,
  useCategories,
  useSearchCommodities,
} from '../../hooks/queries/useCommodities';
import { useNetworkStore } from '../../store/networkStore';
import Input from '../../components/ui/Input';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatPrice } from '../../utils/formatting';
import type { Commodity } from '../../types/models';

type Props = NativeStackScreenProps<PricesStackParamList, 'CommodityList'>;

const ITEM_HEIGHT = 70;

export default function CommodityListScreen({ navigation }: Props) {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [page, setPage] = useState(1);

  const isConnected = useNetworkStore(s => s.isConnected);

  const { data: categories } = useCategories();
  const { data: searchResults, isFetching: searching } = useSearchCommodities(search);
  const {
    data: commoditiesData,
    isLoading,
    refetch,
    isStale,
  } = useCommoditiesWithPrices(page, selectedCategory);

  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  const displayItems: Commodity[] = search.length >= 2
    ? (searchResults?.data ?? [])
    : (commoditiesData?.data?.commodities ?? []);

  const renderItem = useCallback(({ item }: { item: Commodity }) => {
    const change = item.price_change_1d ?? 0;
    const isUp = change > 0;
    const isDown = change < 0;

    return (
      <TouchableOpacity
        style={styles.row}
        onPress={() =>
          navigation.navigate('CommodityDetail', {
            commodityId: item.id,
            commodityName: item.name,
          })
        }
        activeOpacity={0.7}
      >
        <View style={styles.rowLeft}>
          <Text style={styles.commodityName}>{item.name}</Text>
          <View style={styles.categoryBadge}>
            <Text style={styles.categoryText}>{item.category}</Text>
          </View>
        </View>
        <View style={styles.rowRight}>
          <Text style={styles.price}>
            {item.current_price ? formatPrice(item.current_price) : '—'}
          </Text>
          {change !== 0 && (
            <Text
              style={[
                styles.change,
                isUp && styles.changeUp,
                isDown && styles.changeDown,
              ]}
            >
              {isUp ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
            </Text>
          )}
        </View>
      </TouchableOpacity>
    );
  }, [navigation]);

  const getItemLayout = useCallback(
    (_: any, index: number) => ({ length: ITEM_HEIGHT, offset: ITEM_HEIGHT * index, index }),
    [],
  );

  if (isLoading) return <LoadingSpinner fullScreen />;

  return (
    <View style={styles.container}>
      {/* Search */}
      <View style={styles.searchBar}>
        <Input
          placeholder="Search commodities..."
          value={search}
          onChangeText={setSearch}
          style={styles.searchInput}
        />
      </View>

      {/* Offline notice */}
      {!isConnected && isStale && (
        <View style={styles.offlineNotice}>
          <Text style={styles.offlineText}>📡 Showing cached data</Text>
        </View>
      )}

      {/* Category filters */}
      {categories?.data && categories.data.length > 0 && (
        <FlatList
          data={['All', ...categories.data]}
          horizontal
          showsHorizontalScrollIndicator={false}
          keyExtractor={item => item}
          contentContainerStyle={styles.categoryList}
          renderItem={({ item }) => {
            const isSelected =
              item === 'All' ? !selectedCategory : selectedCategory === item;
            return (
              <TouchableOpacity
                style={[styles.chip, isSelected && styles.chipSelected]}
                onPress={() => {
                  setSelectedCategory(item === 'All' ? undefined : item);
                  setPage(1);
                }}
              >
                <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>
                  {item}
                </Text>
              </TouchableOpacity>
            );
          }}
        />
      )}

      {/* List */}
      <FlatList
        data={displayItems}
        keyExtractor={item => item.id}
        renderItem={renderItem}
        getItemLayout={getItemLayout}
        windowSize={5}
        maxToRenderPerBatch={10}
        initialNumToRender={20}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />}
        onEndReached={() => {
          if (!search && commoditiesData?.data?.has_more) {
            setPage(p => p + 1);
          }
        }}
        onEndReachedThreshold={0.3}
        ListEmptyComponent={
          <EmptyState
            icon="🌾"
            message={search ? `No results for "${search}"` : 'No commodities found'}
          />
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  searchBar: { padding: spacing[3], paddingBottom: 0 },
  searchInput: { marginBottom: 0 },
  offlineNotice: {
    backgroundColor: colors.warning,
    paddingVertical: spacing[1],
    paddingHorizontal: spacing[4],
  },
  offlineText: {
    color: '#fff',
    fontSize: typography.fontSize.xs,
    textAlign: 'center',
  },
  categoryList: { paddingHorizontal: spacing[3], paddingVertical: spacing[2] },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    marginRight: spacing[2],
    backgroundColor: colors.background,
  },
  chipSelected: {
    backgroundColor: colors.primary[600],
    borderColor: colors.primary[600],
  },
  chipText: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  chipTextSelected: { color: '#fff', fontWeight: typography.fontWeight.medium },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    height: ITEM_HEIGHT,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.background,
  },
  rowLeft: { flex: 1 },
  rowRight: { alignItems: 'flex-end' },
  commodityName: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.primary,
    marginBottom: 2,
  },
  categoryBadge: {
    backgroundColor: colors.primary[50],
    borderRadius: 4,
    paddingHorizontal: spacing[1],
    paddingVertical: 1,
    alignSelf: 'flex-start',
  },
  categoryText: { fontSize: 10, color: colors.primary[700] },
  price: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
  },
  change: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.medium },
  changeUp: { color: colors.priceUp },
  changeDown: { color: colors.priceDown },
});
