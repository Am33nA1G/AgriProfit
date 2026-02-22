import React, { useRef } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
  RefreshControl,
  Animated,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { MoreStackParamList } from '../../types/navigation';
import { useInventory, useDeleteInventory } from '../../hooks/queries/useInventory';
import Card from '../../components/ui/Card';
import EmptyState from '../../components/ui/EmptyState';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatPrice, formatDate } from '../../utils/formatting';
import type { InventoryItem } from '../../types/models';

type NavProp = NativeStackNavigationProp<MoreStackParamList>;

function InventoryRow({
  item,
  onDelete,
}: {
  item: InventoryItem;
  onDelete: (id: string, name: string) => void;
}) {
  const translateX = useRef(new Animated.Value(0)).current;
  const [swiped, setSwiped] = React.useState(false);

  const handleSwipe = () => {
    if (!swiped) {
      Animated.spring(translateX, {
        toValue: -80,
        useNativeDriver: true,
      }).start();
      setSwiped(true);
    } else {
      Animated.spring(translateX, {
        toValue: 0,
        useNativeDriver: true,
      }).start();
      setSwiped(false);
    }
  };

  const handleDeletePress = () => {
    onDelete(item.id, item.commodity_name);
    Animated.spring(translateX, {
      toValue: 0,
      useNativeDriver: true,
    }).start();
    setSwiped(false);
  };

  return (
    <View style={styles.rowWrapper}>
      {/* Delete background */}
      <View style={styles.deleteBackground}>
        <TouchableOpacity style={styles.deleteButton} onPress={handleDeletePress}>
          <Text style={styles.deleteButtonText}>Delete</Text>
        </TouchableOpacity>
      </View>

      {/* Swipeable row */}
      <Animated.View style={{ transform: [{ translateX }] }}>
        <TouchableOpacity onPress={handleSwipe} activeOpacity={0.95}>
          <Card style={styles.itemCard}>
            <View style={styles.itemHeader}>
              <Text style={styles.commodityName}>{item.commodity_name}</Text>
              {item.market_value != null && (
                <Text style={styles.marketValue}>{formatPrice(item.market_value)}</Text>
              )}
            </View>
            <View style={styles.itemMeta}>
              <View style={styles.metaChip}>
                <Text style={styles.metaText}>
                  {item.quantity} {item.unit}
                </Text>
              </View>
              <Text style={styles.metaSeparator}>•</Text>
              <Text style={styles.storageDate}>
                Stored: {formatDate(item.storage_date)}
              </Text>
            </View>
            {item.notes && (
              <Text style={styles.notes} numberOfLines={1}>
                {item.notes}
              </Text>
            )}
          </Card>
        </TouchableOpacity>
      </Animated.View>
    </View>
  );
}

export default function InventoryScreen() {
  const navigation = useNavigation<NavProp>();
  const { data, isLoading, refetch } = useInventory();
  const { mutate: deleteItem } = useDeleteInventory();
  const [refreshing, setRefreshing] = React.useState(false);

  const items: InventoryItem[] = data?.data ?? [];

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  const handleDelete = (id: string, name: string) => {
    Alert.alert(
      'Delete Item',
      `Remove "${name}" from inventory?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => deleteItem(id),
        },
      ],
    );
  };

  if (isLoading) return <LoadingSpinner fullScreen />;

  return (
    <Screen style={styles.screen}>
      <FlatList
        data={items}
        keyExtractor={item => item.id}
        renderItem={({ item }) => (
          <InventoryRow item={item} onDelete={handleDelete} />
        )}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <EmptyState
            icon="📦"
            message="No inventory items yet"
            actionLabel="Add Item"
            onAction={() => navigation.navigate('AddInventory')}
          />
        }
        showsVerticalScrollIndicator={false}
      />

      {/* FAB */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('AddInventory')}
        activeOpacity={0.85}
      >
        <Text style={styles.fabIcon}>+</Text>
      </TouchableOpacity>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    backgroundColor: colors.surface,
  },
  listContent: {
    padding: spacing[4],
    paddingBottom: spacing[20],
    flexGrow: 1,
  },
  rowWrapper: {
    position: 'relative',
    marginBottom: spacing[3],
  },
  deleteBackground: {
    position: 'absolute',
    right: 0,
    top: 0,
    bottom: 0,
    width: 80,
    borderRadius: 12,
    backgroundColor: colors.error,
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteButton: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    width: 80,
  },
  deleteButtonText: {
    color: colors.text.inverse,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
  },
  itemCard: {
    backgroundColor: colors.background,
  },
  itemHeader: {
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
  marketValue: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary[700],
  },
  itemMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  metaChip: {
    backgroundColor: colors.primary[50],
    borderRadius: 4,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  metaText: {
    fontSize: typography.fontSize.sm,
    color: colors.primary[700],
    fontWeight: typography.fontWeight.medium,
  },
  metaSeparator: {
    fontSize: typography.fontSize.xs,
    color: colors.text.disabled,
  },
  storageDate: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
  notes: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
    marginTop: spacing[2],
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
});
