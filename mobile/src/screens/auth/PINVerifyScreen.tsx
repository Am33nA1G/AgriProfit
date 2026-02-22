import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AuthStackParamList } from '../../types/navigation';
import { verifyPin, tryBiometricRestore, getBiometricSupport } from '../../services/biometric';
import { getBiometricPreference } from '../../services/secureStorage';
import { useAuth } from '../../hooks/useAuth';
import { useAuthStore } from '../../store/authStore';
import Button from '../../components/ui/Button';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

type Props = NativeStackScreenProps<AuthStackParamList, 'PINVerify'>;

const MAX_ATTEMPTS = 3;

export default function PINVerifyScreen({ navigation }: Props) {
  const setAuthenticated = useAuthStore(s => s.setAuthenticated);
  const { logout } = useAuth();

  const [pin, setPin] = useState('');
  const [attempts, setAttempts] = useState(0);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [biometricAvailable, setBiometricAvailable] = useState(false);

  useEffect(() => {
    (async () => {
      const [support, preference] = await Promise.all([
        getBiometricSupport(),
        getBiometricPreference(),
      ]);
      if (support.isSupported && support.hasEnrolled && preference) {
        setBiometricAvailable(true);
        // Auto-prompt biometric on screen load
        handleBiometric();
      }
    })();
  }, []);

  const handleBiometric = async () => {
    const success = await tryBiometricRestore();
    if (success) {
      setAuthenticated(true);
    }
  };

  const handleVerify = async () => {
    if (pin.length < 4) return;

    setIsLoading(true);
    try {
      const valid = await verifyPin(pin);
      if (valid) {
        setAuthenticated(true);
      } else {
        const newAttempts = attempts + 1;
        setAttempts(newAttempts);
        setPin('');

        if (newAttempts >= MAX_ATTEMPTS) {
          Alert.alert(
            'Too many attempts',
            'Please login with OTP',
            [{ text: 'OK', onPress: () => navigation.replace('Login') }],
          );
        } else {
          setError(`Incorrect PIN. ${MAX_ATTEMPTS - newAttempts} attempts remaining.`);
        }
      }
    } catch {
      setError('An error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text style={styles.emoji}>🔐</Text>
        <Text style={styles.title}>Enter PIN</Text>
        <Text style={styles.subtitle}>Enter your PIN to continue</Text>
      </View>

      <TextInput
        style={styles.pinInput}
        value={pin}
        onChangeText={setPin}
        keyboardType="numeric"
        secureTextEntry
        maxLength={6}
        placeholder="••••••"
        placeholderTextColor={colors.text.disabled}
        autoFocus
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Button
        title="Unlock"
        onPress={handleVerify}
        loading={isLoading}
        disabled={pin.length < 4}
        style={styles.btn}
      />

      {biometricAvailable && (
        <TouchableOpacity style={styles.biometricBtn} onPress={handleBiometric}>
          <Text style={styles.biometricText}>Use Biometric</Text>
        </TouchableOpacity>
      )}

      <Button
        title="Use OTP instead"
        variant="outline"
        onPress={() => navigation.replace('Login')}
        style={styles.otpBtn}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: spacing[8],
    paddingBottom: spacing[6],
    alignItems: 'center',
  },
  emoji: { fontSize: 48, marginBottom: spacing[3] },
  title: {
    fontSize: typography.fontSize['2xl'],
    fontWeight: typography.fontWeight.bold,
    color: colors.text.primary,
    marginBottom: spacing[2],
  },
  subtitle: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
  pinInput: {
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: 8,
    padding: spacing[4],
    fontSize: typography.fontSize.xl,
    textAlign: 'center',
    color: colors.text.primary,
    letterSpacing: 12,
    marginBottom: spacing[4],
  },
  error: {
    color: colors.error,
    fontSize: typography.fontSize.sm,
    textAlign: 'center',
    marginBottom: spacing[3],
  },
  btn: { marginTop: spacing[2] },
  biometricBtn: {
    marginTop: spacing[4],
    alignItems: 'center',
    paddingVertical: spacing[3],
  },
  biometricText: {
    color: colors.primary[600],
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.medium,
  },
  otpBtn: { marginTop: spacing[3] },
});
