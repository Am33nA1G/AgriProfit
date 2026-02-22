import React, { useState } from 'react';
import { View, Text, TextInput, ScrollView, StyleSheet, Alert } from 'react-native';
import { useAuthStore } from '../../store/authStore';
import apiClient from '../../api/client';
import Button from '../../components/ui/Button';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

export default function ProfileScreen() {
  const user = useAuthStore(s => s.user);
  const setUser = useAuthStore(s => s.setUser);

  const [name, setName] = useState(user?.name ?? '');
  const [isLoading, setIsLoading] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) {
      Alert.alert('Error', 'Name is required');
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiClient.put('/users/me', { name: name.trim() });
      setUser(response.data);
      Alert.alert('Success', 'Profile updated successfully');
    } catch {
      Alert.alert('Error', 'Failed to update profile. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.avatarSection}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(user?.name ?? user?.phone ?? '?')[0].toUpperCase()}
          </Text>
        </View>
        <Text style={styles.phone}>{user?.phone}</Text>
      </View>

      <View style={styles.form}>
        <Text style={styles.label}>Full Name</Text>
        <TextInput
          style={styles.input}
          value={name}
          onChangeText={setName}
          placeholder="Enter your name"
          placeholderTextColor={colors.text.secondary}
        />

        <Text style={styles.label}>State</Text>
        <View style={styles.readonlyField}>
          <Text style={styles.readonlyText}>{user?.state ?? '—'}</Text>
        </View>

        <Text style={styles.label}>District</Text>
        <View style={styles.readonlyField}>
          <Text style={styles.readonlyText}>{user?.district ?? '—'}</Text>
        </View>

        <Text style={styles.label}>Phone</Text>
        <View style={styles.readonlyField}>
          <Text style={styles.readonlyText}>{user?.phone}</Text>
        </View>
      </View>

      <Button
        title="Save Changes"
        onPress={handleSave}
        loading={isLoading}
        style={styles.saveBtn}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing[4] },
  avatarSection: { alignItems: 'center', paddingVertical: spacing[6] },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.primary[100],
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: spacing[3],
  },
  avatarText: { fontSize: 36, fontWeight: typography.fontWeight.bold, color: colors.primary[700] },
  phone: { fontSize: typography.fontSize.base, color: colors.text.secondary },
  form: { marginBottom: spacing[4] },
  label: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.primary,
    marginBottom: spacing[1],
    marginTop: spacing[3],
  },
  input: {
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: spacing[3],
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
  },
  readonlyField: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: spacing[3],
  },
  readonlyText: { fontSize: typography.fontSize.base, color: colors.text.secondary },
  saveBtn: { marginTop: spacing[4] },
});
