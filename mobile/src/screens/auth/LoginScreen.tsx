import React, { useState } from 'react';
import { View, Text, Alert, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AuthStackParamList } from '../../types/navigation';
import { authApi } from '../../api/auth';
import { validatePhoneNumber } from '../../utils/validation';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

type Props = NativeStackScreenProps<AuthStackParamList, 'Login'>;

export default function LoginScreen({ navigation }: Props) {
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSendOTP = async () => {
    const cleaned = phone.replace(/\D/g, '');
    if (!validatePhoneNumber(cleaned)) {
      setError('Please enter a valid 10-digit mobile number (start with 6-9)');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await authApi.requestOTP(cleaned);
      navigation.navigate('OTP', { phoneNumber: cleaned });
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Failed to send OTP. Please try again.';
      Alert.alert('Error', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen scroll>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.header}>
          <Text style={styles.emoji}>🌱</Text>
          <Text style={styles.title}>AgriProfit</Text>
          <Text style={styles.subtitle}>Smart farming decisions</Text>
        </View>

        <View style={styles.form}>
          <Input
            label="Mobile Number"
            placeholder="Enter 10-digit number"
            value={phone}
            onChangeText={text => {
              setPhone(text.replace(/\D/g, '').slice(0, 10));
              if (error) setError('');
            }}
            phonePrefix
            keyboardType="phone-pad"
            maxLength={10}
            error={error}
            editable={!loading}
          />

          <Button
            title="Send OTP"
            onPress={handleSendOTP}
            loading={loading}
            disabled={phone.length !== 10}
          />
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: 'center',
    paddingTop: spacing[12],
    paddingBottom: spacing[8],
  },
  emoji: {
    fontSize: 56,
    marginBottom: spacing[2],
  },
  title: {
    fontSize: typography.fontSize['3xl'],
    fontWeight: typography.fontWeight.bold,
    color: colors.primary[700],
    marginBottom: spacing[2],
  },
  subtitle: {
    fontSize: typography.fontSize.base,
    color: colors.text.secondary,
  },
  form: {
    gap: spacing[4],
  },
});
