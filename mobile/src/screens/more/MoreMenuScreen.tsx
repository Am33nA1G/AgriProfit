import React from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useAuthStore } from '../../store/authStore';
import { useAuth } from '../../hooks/useAuth';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

interface MenuItem {
  label: string;
  icon: string;
  screen?: string;
  action?: () => void;
  destructive?: boolean;
}

export default function MoreMenuScreen() {
  const navigation = useNavigation<any>();
  const user = useAuthStore(s => s.user);
  const { logout } = useAuth();

  const sections: { title: string; items: MenuItem[] }[] = [
    {
      title: 'My Account',
      items: [
        { label: 'Profile', icon: '👤', screen: 'Profile' },
        { label: 'Settings', icon: '⚙️', screen: 'Settings' },
        { label: 'Notifications', icon: '🔔', screen: 'Notifications' },
      ],
    },
    {
      title: 'Farming',
      items: [
        { label: 'Inventory', icon: '📦', screen: 'Inventory' },
        { label: 'Sales', icon: '💰', screen: 'Sales' },
        { label: 'Community', icon: '💬', screen: 'Community' },
      ],
    },
    {
      title: 'Account',
      items: [
        {
          label: 'Logout',
          icon: '🚪',
          destructive: true,
          action: () => logout(),
        },
      ],
    },
  ];

  return (
    <ScrollView style={styles.container}>
      {/* User header */}
      <View style={styles.userHeader}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(user?.name ?? user?.phone ?? '?')[0].toUpperCase()}
          </Text>
        </View>
        <View>
          <Text style={styles.userName}>{user?.name ?? 'Farmer'}</Text>
          <Text style={styles.userPhone}>{user?.phone}</Text>
          {user?.district && user?.state && (
            <Text style={styles.userLocation}>{user.district}, {user.state}</Text>
          )}
        </View>
      </View>

      {sections.map(section => (
        <View key={section.title} style={styles.section}>
          <Text style={styles.sectionTitle}>{section.title}</Text>
          {section.items.map(item => (
            <TouchableOpacity
              key={item.label}
              style={styles.menuRow}
              onPress={() => item.action ? item.action() : navigation.navigate(item.screen!)}
            >
              <Text style={styles.menuIcon}>{item.icon}</Text>
              <Text style={[styles.menuLabel, item.destructive && styles.destructive]}>
                {item.label}
              </Text>
              {!item.destructive && <Text style={styles.chevron}>›</Text>}
            </TouchableOpacity>
          ))}
        </View>
      ))}

      <Text style={styles.version}>AgriProfit v1.0.0</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  userHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing[5],
    backgroundColor: colors.primary[600],
    gap: spacing[4],
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary[400],
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: { fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: '#fff' },
  userName: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: '#fff' },
  userPhone: { fontSize: typography.fontSize.sm, color: colors.primary[100], marginTop: 2 },
  userLocation: { fontSize: typography.fontSize.xs, color: colors.primary[200], marginTop: 2 },
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
  menuRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[4],
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  menuIcon: { fontSize: 20, marginRight: spacing[3] },
  menuLabel: { flex: 1, fontSize: typography.fontSize.base, color: colors.text.primary },
  destructive: { color: colors.error },
  chevron: { fontSize: 20, color: colors.text.secondary },
  version: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
    textAlign: 'center',
    padding: spacing[6],
  },
});
