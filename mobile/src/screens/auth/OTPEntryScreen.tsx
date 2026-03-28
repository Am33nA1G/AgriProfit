// mobile/src/screens/auth/OTPEntryScreen.tsx
// Phase 2 plan 02-02 — 6-box OTP input with auto-submit, countdown, SMS autofill.

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    KeyboardAvoidingView,
    ScrollView,
    StyleSheet,
    Platform,
    ActivityIndicator,
    Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useMutation } from '@tanstack/react-query';
import * as SecureStore from 'expo-secure-store';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import api from '../../lib/api';
import { useAuthStore } from '../../store/authStore';
import type { AuthStackParamList } from '../../navigation/AuthStack';

type Props = {
    navigation: NativeStackNavigationProp<AuthStackParamList, 'OTPEntry'>;
    route: RouteProp<AuthStackParamList, 'OTPEntry'>;
};

const OTP_LENGTH = 6;
const RESEND_COUNTDOWN = 60;

export function OTPEntryScreen({ navigation, route }: Props) {
    const { phoneNumber } = route.params;
    const [digits, setDigits] = useState<string[]>(Array(OTP_LENGTH).fill(''));
    const [countdown, setCountdown] = useState(RESEND_COUNTDOWN);
    const inputRefs = useRef<(TextInput | null)[]>([]);
    const { setToken, setUser } = useAuthStore();

    useEffect(() => {
        if (countdown <= 0) return;
        const timer = setInterval(() => {
            setCountdown((prev) => {
                if (prev <= 1) { clearInterval(timer); return 0; }
                return prev - 1;
            });
        }, 1000);
        return () => clearInterval(timer);
    }, [countdown]);

    const verifyOtpMutation = useMutation({
        mutationFn: async (otp: string) => {
            const response = await api.post('/auth/verify-otp', {
                phone_number: phoneNumber,
                otp,
            });
            return response.data;
        },
        onSuccess: async (data) => {
            await SecureStore.setItemAsync('auth_token', data.access_token);
            setToken(data.access_token);
            setUser(data.user);
            // RootNavigator re-renders automatically on token set
        },
        onError: (error: unknown) => {
            const message =
                (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                'Invalid OTP. Please try again.';
            Alert.alert('Verification Failed', message);
            setDigits(Array(OTP_LENGTH).fill(''));
            inputRefs.current[0]?.focus();
        },
    });

    const resendMutation = useMutation({
        mutationFn: async () => {
            await api.post('/auth/request-otp', { phone_number: phoneNumber });
        },
        onSuccess: () => {
            setCountdown(RESEND_COUNTDOWN);
            setDigits(Array(OTP_LENGTH).fill(''));
            inputRefs.current[0]?.focus();
            Alert.alert('OTP resent', 'A new code has been sent to your number.');
        },
        onError: () => {
            Alert.alert('Error', 'Failed to resend OTP. Please wait and try again.');
        },
    });

    const handleDigitChange = useCallback(
        (text: string, index: number) => {
            const cleaned = text.replace(/\D/g, '');
            // Handle SMS autofill — full 6-digit paste
            if (cleaned.length === OTP_LENGTH) {
                const newDigits = cleaned.split('');
                setDigits(newDigits);
                inputRefs.current[OTP_LENGTH - 1]?.focus();
                verifyOtpMutation.mutate(cleaned);
                return;
            }
            const digit = cleaned.slice(-1);
            const newDigits = [...digits];
            newDigits[index] = digit;
            setDigits(newDigits);
            if (digit && index < OTP_LENGTH - 1) {
                inputRefs.current[index + 1]?.focus();
            }
            if (digit && index === OTP_LENGTH - 1) {
                const fullOtp = newDigits.join('');
                if (fullOtp.length === OTP_LENGTH) {
                    verifyOtpMutation.mutate(fullOtp);
                }
            }
        },
        [digits, verifyOtpMutation]
    );

    const handleKeyPress = useCallback(
        (event: { nativeEvent: { key: string } }, index: number) => {
            if (event.nativeEvent.key === 'Backspace' && !digits[index] && index > 0) {
                inputRefs.current[index - 1]?.focus();
            }
        },
        [digits]
    );

    return (
        <SafeAreaView style={styles.safeArea}>
            <KeyboardAvoidingView
                style={styles.flex}
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            >
                <ScrollView
                    contentContainerStyle={styles.scrollContent}
                    keyboardShouldPersistTaps="handled"
                >
                    <TouchableOpacity
                        style={styles.backButton}
                        onPress={() => navigation.goBack()}
                    >
                        <Text style={styles.backButtonText}>← Back</Text>
                    </TouchableOpacity>

                    <View style={styles.header}>
                        <View style={styles.iconContainer}>
                            <Text style={styles.iconEmoji}>📱</Text>
                        </View>
                        <Text style={styles.title}>Verify your number</Text>
                        <Text style={styles.subtitle}>
                            Enter the 6-digit code sent to{' '}
                            <Text style={styles.phone}>+91 {phoneNumber}</Text>
                        </Text>
                    </View>

                    <View style={styles.card}>
                        <View style={styles.otpRow}>
                            {digits.map((digit, index) => (
                                <TextInput
                                    key={index}
                                    ref={(ref) => { inputRefs.current[index] = ref; }}
                                    style={[
                                        styles.otpBox,
                                        digit ? styles.otpBoxFilled : null,
                                        verifyOtpMutation.isError ? styles.otpBoxError : null,
                                    ]}
                                    value={digit}
                                    onChangeText={(text) => handleDigitChange(text, index)}
                                    onKeyPress={(e) => handleKeyPress(e, index)}
                                    keyboardType="number-pad"
                                    maxLength={OTP_LENGTH}
                                    textContentType="oneTimeCode"
                                    autoComplete={Platform.OS === 'ios' ? 'one-time-code' : 'sms-otp'}
                                    selectTextOnFocus
                                    autoFocus={index === 0}
                                />
                            ))}
                        </View>

                        {verifyOtpMutation.isPending && (
                            <View style={styles.statusRow}>
                                <ActivityIndicator size="small" color={colors.primary} />
                                <Text style={styles.statusText}>Verifying…</Text>
                            </View>
                        )}

                        <View style={styles.resendRow}>
                            {countdown > 0 ? (
                                <Text style={styles.countdownText}>Resend code in {countdown}s</Text>
                            ) : (
                                <TouchableOpacity
                                    onPress={() => resendMutation.mutate()}
                                    disabled={resendMutation.isPending}
                                >
                                    <Text style={styles.resendLink}>
                                        {resendMutation.isPending ? 'Sending…' : 'Resend code'}
                                    </Text>
                                </TouchableOpacity>
                            )}
                        </View>
                    </View>
                </ScrollView>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    flex: { flex: 1 },
    safeArea: { flex: 1, backgroundColor: colors.surface },
    scrollContent: { flexGrow: 1, paddingHorizontal: spacing[4], paddingVertical: spacing[6] },
    backButton: { marginBottom: spacing[4] },
    backButtonText: { fontSize: typography.fontSize.sm, color: colors.primary, fontWeight: typography.fontWeight.medium },
    header: { alignItems: 'center', marginBottom: spacing[8] },
    iconContainer: { width: 72, height: 72, borderRadius: radii.xl, backgroundColor: colors.primaryLight, justifyContent: 'center', alignItems: 'center', marginBottom: spacing[4] },
    iconEmoji: { fontSize: 36 },
    title: { fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.foreground, marginBottom: spacing[2] },
    subtitle: { fontSize: typography.fontSize.sm, color: colors.muted, textAlign: 'center', lineHeight: 20 },
    phone: { fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    card: { backgroundColor: colors.card, borderRadius: radii.lg, borderWidth: 1, borderColor: colors.border, padding: spacing[6], ...shadows.card },
    otpRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: spacing[4] },
    otpBox: { width: 44, height: 52, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.background, textAlign: 'center', fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    otpBoxFilled: { borderColor: colors.primary, backgroundColor: colors.primaryLight },
    otpBoxError: { borderColor: colors.error, backgroundColor: colors.errorLight },
    statusRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: spacing[3] },
    statusText: { fontSize: typography.fontSize.sm, color: colors.muted },
    resendRow: { alignItems: 'center', marginTop: spacing[2] },
    countdownText: { fontSize: typography.fontSize.sm, color: colors.muted },
    resendLink: { fontSize: typography.fontSize.sm, color: colors.primary, fontWeight: typography.fontWeight.semibold },
});
