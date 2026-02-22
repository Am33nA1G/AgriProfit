import * as LocalAuthentication from 'expo-local-authentication';
import * as Crypto from 'expo-crypto';
import { getBiometricPreference, getPinHash } from './secureStorage';

export interface BiometricSupportInfo {
  isSupported: boolean;
  enrolledTypes: LocalAuthentication.AuthenticationType[];
  hasEnrolled: boolean;
}

/**
 * Check device biometric support and enrollment status.
 */
export async function getBiometricSupport(): Promise<BiometricSupportInfo> {
  const isSupported = await LocalAuthentication.hasHardwareAsync();
  if (!isSupported) {
    return { isSupported: false, enrolledTypes: [], hasEnrolled: false };
  }

  const enrolledTypes = await LocalAuthentication.supportedAuthenticationTypesAsync();
  const hasEnrolled = await LocalAuthentication.isEnrolledAsync();

  return { isSupported, enrolledTypes, hasEnrolled };
}

/**
 * Prompt biometric authentication.
 * Returns true if authenticated, false if failed/cancelled.
 */
export async function authenticateWithBiometric(
  promptMessage = 'Authenticate to continue',
): Promise<boolean> {
  const support = await getBiometricSupport();
  if (!support.isSupported || !support.hasEnrolled) return false;

  const result = await LocalAuthentication.authenticateAsync({
    promptMessage,
    fallbackLabel: 'Use PIN',
    disableDeviceFallback: false,
    cancelLabel: 'Cancel',
  });

  return result.success;
}

/**
 * Try biometric session restore.
 * Returns true if biometric is enabled AND authenticated successfully.
 */
export async function tryBiometricRestore(): Promise<boolean> {
  const [biometricEnabled, support] = await Promise.all([
    getBiometricPreference(),
    getBiometricSupport(),
  ]);

  if (!biometricEnabled || !support.isSupported || !support.hasEnrolled) return false;

  return authenticateWithBiometric('Unlock AgriProfit');
}

/**
 * Hash a PIN using SHA-256 (expo-crypto, works in React Native).
 */
export async function hashPin(pin: string): Promise<string> {
  return Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, pin);
}

/**
 * Verify a PIN against the stored hash.
 */
export async function verifyPin(pin: string): Promise<boolean> {
  const storedHash = await getPinHash();
  if (!storedHash) return false;

  const hash = await hashPin(pin);
  return hash === storedHash;
}
