import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Alert } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AuthStackParamList } from '../../types/navigation';
import apiClient from '../../api/client';
import { authApi } from '../../api/auth';
import { useAuthStore } from '../../store/authStore';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

type Props = NativeStackScreenProps<AuthStackParamList, 'ProfileComplete'>;

export default function ProfileCompleteScreen({ navigation }: Props) {
  const user = useAuthStore(s => s.user);
  const setUser = useAuthStore(s => s.setUser);

  const [name, setName] = useState(user?.name ?? '');
  const [state, setState] = useState(user?.state ?? '');
  const [district, setDistrict] = useState(user?.district ?? '');
  const [states, setStates] = useState<string[]>([]);
  const [districts, setDistricts] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  // If already complete, skip
  useEffect(() => {
    if (user?.is_profile_complete) {
      navigation.replace('PINSetup');
    }
  }, []);

  useEffect(() => {
    apiClient.get<string[]>('/mandis/states').then(r => setStates(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (state) {
      apiClient.get<string[]>(`/mandis/districts?state=${encodeURIComponent(state)}`)
        .then(r => setDistricts(r.data))
        .catch(() => {});
    }
  }, [state]);

  const handleSave = async () => {
    if (!name.trim()) { Alert.alert('Error', 'Name is required'); return; }
    if (!state) { Alert.alert('Error', 'State is required'); return; }
    if (!district) { Alert.alert('Error', 'District is required'); return; }

    setLoading(true);
    try {
      const response = await authApi.completeProfile({ name: name.trim(), state, district });
      setUser(response.data);
      navigation.replace('PINSetup');
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail ?? 'Failed to save profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text style={styles.title}>Complete Your Profile</Text>
        <Text style={styles.subtitle}>Help us personalize your experience</Text>
      </View>

      <Input
        label="Full Name"
        placeholder="Enter your name"
        value={name}
        onChangeText={setName}
        editable={!loading}
      />

      <View style={styles.field}>
        <Text style={styles.label}>State</Text>
        <Text style={styles.hint}>{state || 'Not selected'}</Text>
        {states.slice(0, 10).map(s => (
          <Button
            key={s}
            title={s}
            variant={state === s ? 'primary' : 'outline'}
            onPress={() => { setState(s); setDistrict(''); }}
            style={styles.stateBtn}
          />
        ))}
      </View>

      {state && districts.length > 0 && (
        <View style={styles.field}>
          <Text style={styles.label}>District</Text>
          {districts.slice(0, 10).map(d => (
            <Button
              key={d}
              title={d}
              variant={district === d ? 'primary' : 'outline'}
              onPress={() => setDistrict(d)}
              style={styles.stateBtn}
            />
          ))}
        </View>
      )}

      <Button
        title="Save Profile"
        onPress={handleSave}
        loading={loading}
        style={styles.saveBtn}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingBottom: spacing[6],
  },
  title: {
    fontSize: typography.fontSize['2xl'],
    fontWeight: typography.fontWeight.bold,
    color: colors.text.primary,
    marginBottom: spacing[1],
  },
  subtitle: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
  field: {
    marginBottom: spacing[4],
  },
  label: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.secondary,
    marginBottom: spacing[2],
  },
  hint: {
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
    marginBottom: spacing[2],
  },
  stateBtn: {
    marginBottom: spacing[1],
    minHeight: 40,
  },
  saveBtn: {
    marginTop: spacing[4],
  },
});
