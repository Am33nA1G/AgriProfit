// mobile/src/hooks/useAuthInit.ts
// Runs once on mount to restore auth session from SecureStore.
// Validates token via /auth/me — clears if expired or invalid.

import { useEffect } from 'react';
import * as SecureStore from 'expo-secure-store';
import { useAuthStore } from '../store/authStore';
import api from '../lib/api';

export function useAuthInit() {
    const { setToken, setUser, setLoading, clearAuth } = useAuthStore();

    useEffect(() => {
        let cancelled = false;

        async function initAuth() {
            try {
                const storedToken = await SecureStore.getItemAsync('auth_token');

                if (!storedToken) {
                    if (!cancelled) {
                        clearAuth();
                        setLoading(false);
                    }
                    return;
                }

                // Validate token still works — also hydrates user data
                const response = await api.get('/auth/me');

                if (!cancelled) {
                    setToken(storedToken);
                    setUser(response.data);
                    setLoading(false);
                }
            } catch {
                // Token expired / invalid / network failure at startup
                if (!cancelled) {
                    try {
                        await SecureStore.deleteItemAsync('auth_token');
                    } catch {
                        // ignore
                    }
                    clearAuth();
                    setLoading(false);
                }
            }
        }

        initAuth();
        return () => {
            cancelled = true;
        };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
}
