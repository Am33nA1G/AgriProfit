import { create } from 'zustand';
import { User } from '@/types';

// Helper to safely access localStorage (SSR-safe)
const getStoredToken = (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('token');
};

const getStoredUser = (): User | null => {
    if (typeof window === 'undefined') return null;
    const stored = localStorage.getItem('user');
    if (!stored) return null;
    try {
        return JSON.parse(stored);
    } catch {
        return null;
    }
};

interface AuthState {
    user: User | null;
    token: string | null;
    isHydrated: boolean;
    setAuth: (user: User, token: string) => void;
    clearAuth: () => void;
    hydrate: () => void;
    isAuthenticated: boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
    user: null,
    token: null,
    isAuthenticated: false,
    isHydrated: false,
    setAuth: (user, token) => {
        if (typeof window !== 'undefined') {
            localStorage.setItem('token', token);
            localStorage.setItem('user', JSON.stringify(user));
        }
        set({ user, token, isAuthenticated: true });
    },
    clearAuth: () => {
        if (typeof window !== 'undefined') {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
        }
        set({ user: null, token: null, isAuthenticated: false });
    },
    hydrate: () => {
        const token = getStoredToken();
        const user = getStoredUser();
        set({
            token,
            user,
            isAuthenticated: !!(token && user),
            isHydrated: true,
        });
    },
}));