import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNetworkStore } from '../../store/networkStore';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

export default function OfflineBanner() {
  const isConnected = useNetworkStore(s => s.isConnected);

  if (isConnected) return null;

  return (
    <View style={styles.banner}>
      <Text style={styles.text}>📡 You are offline</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: colors.warning,
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[4],
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    color: '#fff',
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
  },
});
