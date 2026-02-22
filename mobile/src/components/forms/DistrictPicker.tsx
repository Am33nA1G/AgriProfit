import React, { useState } from 'react';
import {
  View,
  Text,
  Modal,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../api/client';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import LoadingSpinner from '../ui/LoadingSpinner';

interface DistrictPickerProps {
  selectedState?: string;
  selectedDistrict?: string;
  onChange: (district: string) => void;
  placeholder?: string;
}

export default function DistrictPicker({
  selectedState,
  selectedDistrict,
  onChange,
  placeholder = 'Select district...',
}: DistrictPickerProps) {
  const [visible, setVisible] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['mandis', 'districts', selectedState],
    queryFn: () =>
      apiClient.get<string[]>('/mandis/districts', {
        params: { state: selectedState },
      }),
    staleTime: 60 * 60 * 1000,
    enabled: !!selectedState,
  });

  const districts: string[] = data?.data ?? [];

  const handleSelect = (district: string) => {
    onChange(district);
    setVisible(false);
  };

  const isDisabled = !selectedState;

  return (
    <>
      <TouchableOpacity
        style={[styles.trigger, isDisabled && styles.triggerDisabled]}
        onPress={() => { if (!isDisabled) setVisible(true); }}
        activeOpacity={isDisabled ? 1 : 0.7}
      >
        <Text
          style={
            selectedDistrict
              ? styles.selectedText
              : isDisabled
              ? styles.placeholderDisabled
              : styles.placeholder
          }
        >
          {selectedDistrict ?? placeholder}
        </Text>
        <Text style={styles.chevron}>▼</Text>
      </TouchableOpacity>

      <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
        <SafeAreaView style={styles.modal}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>
              Select District{selectedState ? ` — ${selectedState}` : ''}
            </Text>
            <TouchableOpacity onPress={() => setVisible(false)}>
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>

          {isLoading ? (
            <LoadingSpinner fullScreen />
          ) : (
            <FlatList
              data={districts}
              keyExtractor={item => item}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.item,
                    item === selectedDistrict && styles.itemSelected,
                  ]}
                  onPress={() => handleSelect(item)}
                  activeOpacity={0.7}
                >
                  <Text
                    style={[
                      styles.itemText,
                      item === selectedDistrict && styles.itemTextSelected,
                    ]}
                  >
                    {item}
                  </Text>
                  {item === selectedDistrict && (
                    <Text style={styles.checkmark}>✓</Text>
                  )}
                </TouchableOpacity>
              )}
              ListEmptyComponent={
                <View style={styles.empty}>
                  <Text style={styles.emptyText}>
                    {selectedState
                      ? `No districts found for ${selectedState}`
                      : 'Select a state first'}
                  </Text>
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
  triggerDisabled: {
    backgroundColor: colors.surface,
    opacity: 0.6,
  },
  placeholder: {
    fontSize: typography.fontSize.base,
    color: colors.text.disabled,
    flex: 1,
  },
  placeholderDisabled: {
    fontSize: typography.fontSize.base,
    color: colors.text.disabled,
    flex: 1,
  },
  selectedText: {
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
    fontWeight: typography.fontWeight.medium,
    flex: 1,
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
    flex: 1,
    marginRight: spacing[2],
  },
  cancelText: {
    fontSize: typography.fontSize.base,
    color: colors.primary[600],
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[4],
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  itemSelected: {
    backgroundColor: colors.primary[50],
  },
  itemText: {
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
  },
  itemTextSelected: {
    color: colors.primary[700],
    fontWeight: typography.fontWeight.medium,
  },
  checkmark: {
    fontSize: typography.fontSize.base,
    color: colors.primary[600],
    fontWeight: typography.fontWeight.bold,
  },
  empty: {
    padding: spacing[8],
    alignItems: 'center',
  },
  emptyText: {
    fontSize: typography.fontSize.base,
    color: colors.text.secondary,
    textAlign: 'center',
  },
});
