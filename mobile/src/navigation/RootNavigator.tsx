// mobile/src/navigation/RootNavigator.tsx
// Conditional navigator: unauthenticated → AuthStack; authenticated → MainTabs.
// Also wires the API 401 handler and runs auth initialization.

import React, { useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { AuthStack } from './AuthStack';
import { MainTabs } from './MainTabs';
import { useAuthStore } from '../store/authStore';
import { useAuthInit } from '../hooks/useAuthInit';
import { setUnauthorizedHandler } from '../lib/api';
import { colors } from '../theme/tokens';

function AppNavigator() {
    const token = useAuthStore((s) => s.token);
    const isLoading = useAuthStore((s) => s.isLoading);
    const logout = useAuthStore((s) => s.logout);

    // Wire API-02: 401 response → logout + redirect to auth
    useEffect(() => {
        setUnauthorizedHandler(() => {
            logout();
        });
    }, [logout]);

    if (isLoading) {
        return (
            <View
                style={{
                    flex: 1,
                    justifyContent: 'center',
                    alignItems: 'center',
                    backgroundColor: colors.background,
                }}
            >
                <ActivityIndicator size="large" color={colors.primary} />
            </View>
        );
    }

    return token ? <MainTabs /> : <AuthStack />;
}

export function RootNavigator() {
    useAuthInit();

    return (
        <NavigationContainer>
            <AppNavigator />
        </NavigationContainer>
    );
}
