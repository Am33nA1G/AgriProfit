// mobile/src/lib/api.ts
// Axios client for AgriProfit Mobile.
// Mirrors frontend/src/lib/api.ts for React Native (no window/localStorage).

import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// Base URL from Expo env var — set in mobile/.env as EXPO_PUBLIC_API_URL
const BASE_URL =
    (process.env.EXPO_PUBLIC_API_URL as string | undefined) ??
    'http://localhost:8000/api/v1';

export const api = axios.create({
    baseURL: BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
    },
});

// ─── Request interceptor: attach JWT ─────────────────────────────────────────

api.interceptors.request.use(
    async (config) => {
        try {
            const token = await SecureStore.getItemAsync('auth_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        } catch {
            // SecureStore unavailable — proceed without token
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ─── Response interceptor: handle 401 (API-02) ───────────────────────────────

// Handler set by RootNavigator after navigation mounts — breaks circular dep
let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void) {
    onUnauthorized = handler;
}

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            try {
                await SecureStore.deleteItemAsync('auth_token');
            } catch {
                // ignore
            }
            if (onUnauthorized) {
                onUnauthorized();
            }
        }
        return Promise.reject(error);
    }
);

export default api;
