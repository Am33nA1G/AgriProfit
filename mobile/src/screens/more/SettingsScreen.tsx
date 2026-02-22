import React from 'react';
import { View, Text, Switch, TouchableOpacity, ScrollView, StyleSheet, Alert } from 'react-native';
import { useSettingsStore } from '../../store/settingsStore';
import { useAuthStore } from '../../store/authStore';
import { useOfflineQueueStore } from '../../store/offlineQueueStore';
import { useTranslation } from 'react-i18next';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

export default function SettingsScreen() {
  const { language, setLanguage } = useSettingsStore();
  const biometricEnabled = useAuthStore(s => s.biometricEnabled);
  const setBiometricEnabled = useAuthStore(s => s.setBiometricEnabled);
  const { queue, clearCompleted } = useOfflineQueueStore();
  const { i18n } = useTranslation();

  const pendingCount = queue.filter(op => op.status === 'pending' || op.status === 'syncing').length;
  const failedCount = queue.filter(op => op.status === 'failed').length;

  const handleLanguageToggle = () => {
    const newLang = language === 'en' ? 'hi' : 'en';
    setLanguage(newLang);
    i18n.changeLanguage(newLang);
  };

  const handleClearQueue = () => {
    Alert.alert(
      'Clear Sync Queue',
      `This will remove ${failedCount} failed operation(s). This cannot be undone.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: () => {
            useOfflineQueueStore.setState(state => ({
              queue: state.queue.filter(op => op.status !== 'failed'),
            }));
          },
        },
      ],
    );
  };

  return (
    <ScrollView style={styles.container}>
      {/* Language */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Display</Text>
        <View style={styles.row}>
          <View>
            <Text style={styles.rowLabel}>Language / भाषा</Text>
            <Text style={styles.rowSubtitle}>{language === 'en' ? 'English' : 'हिंदी'}</Text>
          </View>
          <Switch
            value={language === 'hi'}
            onValueChange={handleLanguageToggle}
            trackColor={{ false: colors.border, true: colors.primary[400] }}
            thumbColor={language === 'hi' ? colors.primary[600] : '#f4f3f4'}
          />
        </View>
      </View>

      {/* Security */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Security</Text>
        <View style={styles.row}>
          <View>
            <Text style={styles.rowLabel}>Biometric Unlock</Text>
            <Text style={styles.rowSubtitle}>Use fingerprint or face ID to unlock</Text>
          </View>
          <Switch
            value={biometricEnabled}
            onValueChange={setBiometricEnabled}
            trackColor={{ false: colors.border, true: colors.primary[400] }}
            thumbColor={biometricEnabled ? colors.primary[600] : '#f4f3f4'}
          />
        </View>
      </View>

      {/* Offline Queue */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Offline Sync</Text>
        <View style={styles.infoRow}>
          <Text style={styles.rowLabel}>Pending Operations</Text>
          <Text style={[styles.badge, pendingCount > 0 && styles.badgeWarning]}>{pendingCount}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.rowLabel}>Failed Operations</Text>
          <Text style={[styles.badge, failedCount > 0 && styles.badgeError]}>{failedCount}</Text>
        </View>
        {failedCount > 0 && (
          <TouchableOpacity style={styles.clearBtn} onPress={handleClearQueue}>
            <Text style={styles.clearBtnText}>Clear Failed Operations</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* About */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.infoRow}>
          <Text style={styles.rowLabel}>Version</Text>
          <Text style={styles.rowValue}>1.0.0</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.rowLabel}>Build</Text>
          <Text style={styles.rowValue}>001</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  section: { marginBottom: spacing[1] },
  sectionTitle: {
    fontSize: typography.fontSize.xs,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.secondary,
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[1],
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rowLabel: { fontSize: typography.fontSize.base, color: colors.text.primary },
  rowSubtitle: { fontSize: typography.fontSize.xs, color: colors.text.secondary, marginTop: 2 },
  rowValue: { fontSize: typography.fontSize.sm, color: colors.text.secondary },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  badge: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: 12,
    backgroundColor: colors.surface,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.secondary,
    overflow: 'hidden',
  },
  badgeWarning: { backgroundColor: '#fef3c7', color: '#d97706' },
  badgeError: { backgroundColor: '#fee2e2', color: colors.error },
  clearBtn: {
    margin: spacing[4],
    padding: spacing[3],
    backgroundColor: '#fee2e2',
    borderRadius: 8,
    alignItems: 'center',
  },
  clearBtnText: { color: colors.error, fontWeight: typography.fontWeight.medium, fontSize: typography.fontSize.sm },
});
