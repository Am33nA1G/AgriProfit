import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { useOfflineQueue } from '../../hooks/useOfflineQueue';
import { processOfflineQueue } from '../../services/offlineQueue';
import { queryClient } from '../../api/queryClient';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

export default function SyncStatus() {
  const { pendingCount, failedCount, isSyncing } = useOfflineQueue();

  if (pendingCount === 0 && failedCount === 0 && !isSyncing) return null;

  const handleRetry = async () => {
    const result = await processOfflineQueue();
    if (result.synced > 0) {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      queryClient.invalidateQueries({ queryKey: ['community'] });
    }
    if (result.failed > 0) {
      Alert.alert('Sync incomplete', `${result.failed} operation(s) failed to sync.`);
    }
  };

  return (
    <View style={[styles.bar, isSyncing ? styles.syncing : failedCount > 0 ? styles.failed : styles.pending]}>
      {isSyncing ? (
        <>
          <ActivityIndicator size="small" color="#fff" style={styles.spinner} />
          <Text style={styles.text}>Syncing offline changes...</Text>
        </>
      ) : failedCount > 0 ? (
        <>
          <Text style={styles.text}>⚠️ {failedCount} change(s) failed to sync</Text>
          <TouchableOpacity onPress={handleRetry} style={styles.retryBtn}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </>
      ) : (
        <Text style={styles.text}>⏳ {pendingCount} change(s) pending sync</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
  },
  pending: { backgroundColor: colors.warning },
  syncing: { backgroundColor: colors.primary[500] },
  failed: { backgroundColor: colors.error },
  spinner: { marginRight: spacing[2] },
  text: { flex: 1, color: '#fff', fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.medium },
  retryBtn: {
    paddingHorizontal: spacing[3],
    paddingVertical: 4,
    backgroundColor: 'rgba(255,255,255,0.25)',
    borderRadius: 4,
  },
  retryText: { color: '#fff', fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold },
});
