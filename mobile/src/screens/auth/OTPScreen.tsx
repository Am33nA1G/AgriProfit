import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, Alert, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AuthStackParamList } from '../../types/navigation';
import { authApi } from '../../api/auth';
import { useAuth } from '../../hooks/useAuth';
import OTPInput from '../../components/forms/OTPInput';
import Button from '../../components/ui/Button';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { OTP_EXPIRY_SECONDS, OTP_RESEND_COOLDOWN_SECONDS } from '../../utils/constants';

type Props = NativeStackScreenProps<AuthStackParamList, 'OTP'>;

export default function OTPScreen({ route, navigation }: Props) {
  const { phoneNumber } = route.params;
  const { login } = useAuth();

  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [attempts, setAttempts] = useState(0);
  const [countdown, setCountdown] = useState(OTP_EXPIRY_SECONDS);
  const [resendCooldown, setResendCooldown] = useState(OTP_RESEND_COOLDOWN_SECONDS);
  const [isResending, setIsResending] = useState(false);

  // Main countdown
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => setCountdown(c => c - 1), 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  // Resend cooldown
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => setResendCooldown(c => c - 1), 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleVerify = useCallback(async (otpCode: string) => {
    if (otpCode.length !== 6) return;
    if (attempts >= 3) {
      Alert.alert('Too many attempts', 'Please request a new OTP.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await login(phoneNumber, otpCode);
      if (result.needsProfileComplete) {
        navigation.replace('ProfileComplete');
      } else {
        navigation.replace('PINSetup');
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Invalid OTP. Please try again.';
      setError(msg);
      setAttempts(a => a + 1);
      setCode('');
    } finally {
      setLoading(false);
    }
  }, [attempts, login, navigation, phoneNumber]);

  // Auto-submit when all 6 digits entered
  useEffect(() => {
    if (code.length === 6) {
      handleVerify(code);
    }
  }, [code, handleVerify]);

  const handleResend = async () => {
    if (isResending) return;

    setIsResending(true);
    try {
      await authApi.requestOTP(phoneNumber);
      setCountdown(OTP_EXPIRY_SECONDS);
      setResendCooldown(OTP_RESEND_COOLDOWN_SECONDS);
      setAttempts(0);
      setError('');
      setCode('');
      Alert.alert('Success', 'OTP sent successfully');
    } catch {
      Alert.alert('Error', 'Failed to resend OTP. Please try again.');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text style={styles.title}>Verify OTP</Text>
        <Text style={styles.subtitle}>
          Enter the 6-digit code sent to{'\n'}+91 {phoneNumber}
        </Text>
        {countdown > 0 && (
          <Text style={styles.timer}>Expires in {countdown}s</Text>
        )}
      </View>

      <OTPInput onChange={setCode} disabled={loading} />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <View style={styles.actions}>
        <Button
          title="Verify"
          onPress={() => handleVerify(code)}
          loading={loading}
          disabled={code.length !== 6 || loading}
        />

        <Button
          title={resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend OTP'}
          onPress={handleResend}
          variant="outline"
          disabled={resendCooldown > 0 || isResending}
          loading={isResending}
          style={styles.resendBtn}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: 'center',
    paddingTop: spacing[8],
    paddingBottom: spacing[8],
    gap: spacing[2],
  },
  title: {
    fontSize: typography.fontSize['2xl'],
    fontWeight: typography.fontWeight.bold,
    color: colors.text.primary,
  },
  subtitle: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
    textAlign: 'center',
    lineHeight: 20,
  },
  timer: {
    fontSize: typography.fontSize.sm,
    color: colors.warning,
    fontWeight: typography.fontWeight.medium,
  },
  error: {
    color: colors.error,
    fontSize: typography.fontSize.sm,
    textAlign: 'center',
    marginTop: spacing[3],
  },
  actions: {
    marginTop: spacing[6],
    gap: spacing[3],
  },
  resendBtn: {
    marginTop: spacing[2],
  },
});
