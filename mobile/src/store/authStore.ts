import { create } from 'zustand';
import { User } from '../types/models';
import { clearTokens } from '../services/secureStorage';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  biometricEnabled: boolean;
  isLoading: boolean;
}

interface AuthActions {
  setUser: (user: User | null) => void;
  setAuthenticated: (value: boolean) => void;
  setBiometricEnabled: (enabled: boolean) => void;
  setLoading: (loading: boolean) => void;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState & AuthActions>(set => ({
  user: null,
  isAuthenticated: false,
  biometricEnabled: false,
  isLoading: true,

  setUser: user => set({ user }),
  setAuthenticated: isAuthenticated => set({ isAuthenticated }),
  setBiometricEnabled: biometricEnabled => set({ biometricEnabled }),
  setLoading: isLoading => set({ isLoading }),

  logout: async () => {
    await clearTokens();

    // Call backend logout (fire-and-forget)
    try {
      const { default: authApi } = await import('../api/auth');
      await authApi.logout();
    } catch {
      // Ignore errors - local logout succeeded
    }

    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },
}));
