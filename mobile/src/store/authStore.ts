// mobile/src/store/authStore.ts
// Zustand client state store for auth session.
// API-04: zustand only — no Redux, Jotai, or other state libraries.

import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

export interface AuthUser {
    id: string;
    phone_number: string;
    name?: string;
    state?: string;
    district?: string;
    age?: number;
    role: 'user' | 'admin';
    is_active: boolean;
}

interface AuthState {
    token: string | null;
    user: AuthUser | null;
    isLoading: boolean;

    setToken: (token: string) => void;
    setUser: (user: AuthUser) => void;
    setLoading: (loading: boolean) => void;
    clearAuth: () => void;
    logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()((set) => ({
    token: null,
    user: null,
    isLoading: true,     // true on startup — reading SecureStore

    setToken: (token) => set({ token }),
    setUser: (user) => set({ user }),
    setLoading: (isLoading) => set({ isLoading }),
    clearAuth: () => set({ token: null, user: null }),

    logout: async () => {
        try {
            await SecureStore.deleteItemAsync('auth_token');
        } catch {
            // ignore cleanup failure
        }
        set({ token: null, user: null });
        // RootNavigator reacts to token=null → renders AuthStack automatically
    },
}));
