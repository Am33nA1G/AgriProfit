import React, { useState } from 'react';
import { View, Text, TextInput, Alert, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AuthStackParamList } from '../../types/navigation';
import { savePinHash, saveBiometricPreference } from '../../services/secureStorage';
import { hashPin } from '../../services/biometric';
import { getBiometricSupport } from '../../services/biometric';
import { useAuthStore } from '../../store/authStore';
import Button from '../../components/ui/Button';
import Screen from '../../components/layout/Screen';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { PIN_MIN_LENGTH } from '../../utils/constants';

type Props = NativeStackScreenProps<AuthStackParamList, 'PINSetup'>;

type Step = 'enter' | 'confirm';

export default function PINSetupScreen({ navigation }: Props) {
  const setBiometricEnabled = useAuthStore(s => s.setBiometricEnabled);
  const setAuthenticated = useAuthStore(s => s.setAuthenticated);

  const [step, setStep] = useState<Step>('enter');
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleNext = () => {
    if (pin.length < PIN_MIN_LENGTH) {
      setError(`PIN must be at least ${PIN_MIN_LENGTH} digits`);
      return;
    }
    setError('');
    setStep('confirm');
  };

  const handleConfirm = async () => {
    if (pin !== confirmPin) {
      setError('PINs do not match. Please try again.');
      setConfirmPin('');
      return;
    }

    setIsLoading(true);
    try {
      // Hash using expo-crypto (React Native compatible)
      const hash = await hashPin(pin);
      await savePinHash(hash);

      // Check if biometric is available on device
      const support = await getBiometricSupport();

      if (support.isSupported && support.hasEnrolled) {
        Alert.alert(
          'Enable Biometric Unlock?',
          'Use fingerprint or face ID for quick access',
          [
            {
              text: 'Yes, Enable',
              onPress: async () => {
                await saveBiometricPreference(true);
                setBiometricEnabled(true);
                setAuthenticated(true);
              },
            },
            {
              text: 'Use PIN Only',
              onPress: async () => {
                await saveBiometricPreference(false);
                setAuthenticated(true);
              },
            },
          ],
        );
      } else {
        // No biometric hardware — skip prompt
        setAuthenticated(true);
      }
    } catch {
      setError('Failed to save PIN. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text style={styles.title}>{step === 'enter' ? 'Set PIN' : 'Confirm PIN'}</Text>
        <Text style={styles.subtitle}>
          {step === 'enter'
            ? 'Create a 4-6 digit PIN for quick access'
            : 'Re-enter your PIN to confirm'}
        </Text>
      </View>

      <TextInput
        style={styles.pinInput}
        value={step === 'enter' ? pin : confirmPin}
        onChangeText={step === 'enter' ? setPin : setConfirmPin}
        keyboardType="numeric"
        secureTextEntry
        maxLength={6}
        placeholder="••••••"
        placeholderTextColor={colors.text.disabled}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Button
        title={step === 'enter' ? 'Next' : 'Confirm'}
        onPress={step === 'enter' ? handleNext : handleConfirm}
        style={styles.btn}
        loading={isLoading}
        disabled={step === 'enter' ? pin.length < PIN_MIN_LENGTH : confirmPin.length < PIN_MIN_LENGTH}
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
  title: {
    fontSize: typography.fontSize['2xl'],
    fontWeight: typography.fontWeight.bold,
    color: colors.text.primary,
    marginBottom: spacing[2],
  },
  subtitle: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
    textAlign: 'center',
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
  btn: {
    marginTop: spacing[2],
  },
});
