// mobile/src/screens/auth/PhoneEntryScreen.tsx
// Phase 2 plan 02-01 — stub for Phase 1 navigation shell.

import React, { useRef, useState } from 'react';
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
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import api from '../../lib/api';
import type { AuthStackParamList } from '../../navigation/AuthStack';

type Props = {
    navigation: NativeStackNavigationProp<AuthStackParamList, 'PhoneEntry'>;
};

function isValidIndianPhone(phone: string): boolean {
    return /^[6-9]\d{9}$/.test(phone);
}

export function PhoneEntryScreen({ navigation }: Props) {
    const [phoneNumber, setPhoneNumber] = useState('');
    const inputRef = useRef<TextInput>(null);

    const requestOtpMutation = useMutation({
        mutationFn: async (phone: string) => {
            const response = await api.post('/auth/request-otp', { phone_number: phone });
            return response.data;
        },
        onSuccess: (_data, phone) => {
            navigation.navigate('OTPEntry', { phoneNumber: phone });
        },
        onError: (error: unknown) => {
            const message =
                (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                'Failed to send OTP. Please try again.';
            Alert.alert('Error', message);
        },
    });

    const handleSendOTP = () => {
        const cleaned = phoneNumber.trim();
        if (!isValidIndianPhone(cleaned)) {
            Alert.alert(
                'Invalid number',
                'Enter a valid 10-digit Indian mobile number (starting with 6, 7, 8, or 9).'
            );
            return;
        }
        requestOtpMutation.mutate(cleaned);
    };

    return (
        <SafeAreaView style={styles.safeArea}>
            <KeyboardAvoidingView
                style={styles.flex}
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 20}
            >
                <ScrollView
                    contentContainerStyle={styles.scrollContent}
                    keyboardShouldPersistTaps="handled"
                >
                    {/* Branding */}
                    <View style={styles.header}>
                        <View style={styles.logoMark}>
                            <Text style={styles.logoEmoji}>🌾</Text>
                        </View>
                        <Text style={styles.appName}>AgriProfit</Text>
                        <Text style={styles.tagline}>Real-time market prices for Indian farmers</Text>
                    </View>

                    {/* Card */}
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>Sign in with OTP</Text>
                        <Text style={styles.cardSubtitle}>
                            Enter your mobile number to receive a one-time password.
                        </Text>

                        {/* Phone input */}
                        <View style={styles.inputGroup}>
                            <Text style={styles.label}>Mobile Number</Text>
                            <View style={styles.phoneRow}>
                                <View style={styles.prefix}>
                                    <Text style={styles.prefixText}>+91</Text>
                                </View>
                                <TextInput
                                    ref={inputRef}
                                    style={styles.phoneInput}
                                    value={phoneNumber}
                                    onChangeText={(text) =>
                                        setPhoneNumber(text.replace(/\D/g, '').slice(0, 10))
                                    }
                                    keyboardType="number-pad"
                                    maxLength={10}
                                    placeholder="Enter 10-digit number"
                                    placeholderTextColor={colors.placeholder}
                                    returnKeyType="done"
                                    onSubmitEditing={handleSendOTP}
                                    autoFocus
                                />
                            </View>
                        </View>

                        <TouchableOpacity
                            style={[
                                styles.button,
                                (requestOtpMutation.isPending || phoneNumber.length < 10) &&
                                styles.buttonDisabled,
                            ]}
                            onPress={handleSendOTP}
                            disabled={requestOtpMutation.isPending || phoneNumber.length < 10}
                            activeOpacity={0.8}
                        >
                            {requestOtpMutation.isPending ? (
                                <ActivityIndicator color={colors.background} />
                            ) : (
                                <Text style={styles.buttonText}>Send OTP</Text>
                            )}
                        </TouchableOpacity>

                        <Text style={styles.disclaimer}>
                            OTP will be sent to +91 {phoneNumber || 'XXXXXXXXXX'}.
                        </Text>
                    </View>
                </ScrollView>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    flex: { flex: 1 },
    safeArea: { flex: 1, backgroundColor: colors.surface },
    scrollContent: {
        flexGrow: 1,
        justifyContent: 'center',
        paddingHorizontal: spacing[4],
        paddingVertical: spacing[8],
    },
    header: { alignItems: 'center', marginBottom: spacing[8] },
    logoMark: {
        width: 72,
        height: 72,
        borderRadius: radii.xl,
        backgroundColor: colors.primaryLight,
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: spacing[3],
    },
    logoEmoji: { fontSize: 36 },
    appName: {
        fontSize: typography.fontSize['2xl'],
        fontWeight: typography.fontWeight.bold,
        color: colors.primary,
        marginBottom: spacing[1],
    },
    tagline: {
        fontSize: typography.fontSize.sm,
        color: colors.muted,
        textAlign: 'center',
    },
    card: {
        backgroundColor: colors.card,
        borderRadius: radii.lg,
        borderWidth: 1,
        borderColor: colors.border,
        padding: spacing[6],
        ...shadows.card,
    },
    cardTitle: {
        fontSize: typography.fontSize.xl,
        fontWeight: typography.fontWeight.semibold,
        color: colors.foreground,
        marginBottom: spacing[2],
    },
    cardSubtitle: {
        fontSize: typography.fontSize.sm,
        color: colors.muted,
        marginBottom: spacing[6],
        lineHeight: 20,
    },
    inputGroup: { marginBottom: spacing[4] },
    label: {
        fontSize: typography.fontSize.sm,
        fontWeight: typography.fontWeight.medium,
        color: colors.foreground,
        marginBottom: spacing[1],
    },
    phoneRow: {
        flexDirection: 'row',
        alignItems: 'center',
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radii.md,
        overflow: 'hidden',
        backgroundColor: colors.background,
    },
    prefix: {
        backgroundColor: colors.surface,
        paddingHorizontal: spacing[3],
        paddingVertical: spacing[3],
        borderRightWidth: 1,
        borderRightColor: colors.border,
    },
    prefixText: {
        fontSize: typography.fontSize.base,
        fontWeight: typography.fontWeight.medium,
        color: colors.foreground,
    },
    phoneInput: {
        flex: 1,
        paddingHorizontal: spacing[3],
        paddingVertical: spacing[3],
        fontSize: typography.fontSize.base,
        color: colors.foreground,
    },
    button: {
        backgroundColor: colors.primary,
        borderRadius: radii.md,
        paddingVertical: spacing[4],
        alignItems: 'center',
        marginBottom: spacing[3],
    },
    buttonDisabled: { backgroundColor: colors.disabled },
    buttonText: {
        fontSize: typography.fontSize.base,
        fontWeight: typography.fontWeight.semibold,
        color: colors.background,
    },
    disclaimer: {
        fontSize: typography.fontSize.xs,
        color: colors.mutedLight,
        textAlign: 'center',
    },
});
