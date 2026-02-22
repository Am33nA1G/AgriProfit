import { authApi } from '../api/auth';
import { useAuthStore } from '../store/authStore';
import { saveTokens, getAccessToken, getRefreshToken, clearTokens, getBiometricPreference } from '../services/secureStorage';
import { registerForPushNotifications, deactivatePushToken } from '../services/pushNotifications';
import { queryClient } from '../api/queryClient';

export function useAuth() {
  const { setUser, setAuthenticated, setLoading, setBiometricEnabled, logout: storeLogout } = useAuthStore();

  /**
   * Called after OTP is verified — saves tokens, sets user, registers push token.
   * Returns { needsProfileComplete }
   */
  const login = async (phoneNumber: string, otp: string) => {
    const response = await authApi.verifyOTP(phoneNumber, otp);
    const { access_token, refresh_token, user } = response.data;

    await saveTokens(access_token, refresh_token);
    setUser(user);
    setAuthenticated(true);

    const biometricEnabled = await getBiometricPreference();
    setBiometricEnabled(biometricEnabled);

    // Register push token (best-effort, non-blocking)
    registerForPushNotifications().catch(() => {});

    return {
      needsProfileComplete: !user.is_profile_complete,
    };
  };

  /**
   * Check auth state on app launch.
   * Tries token → refresh → clears on failure.
   */
  const checkAuthOnLaunch = async () => {
    setLoading(true);
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) {
        setLoading(false);
        return;
      }

      try {
        const response = await authApi.getCurrentUser();
        setUser(response.data);
        setAuthenticated(true);
        const biometricEnabled = await getBiometricPreference();
        setBiometricEnabled(biometricEnabled);
        return;
      } catch (err: any) {
        if (err?.response?.status !== 401) throw err;
      }

      // Access token expired — try refresh
      const refreshToken = await getRefreshToken();
      if (!refreshToken) {
        await clearTokens();
        setLoading(false);
        return;
      }

      try {
        const refreshResponse = await authApi.refreshToken(refreshToken);
        const { access_token, refresh_token: newRefresh } = refreshResponse.data;
        await saveTokens(access_token, newRefresh);

        const meResponse = await authApi.getCurrentUser();
        setUser(meResponse.data);
        setAuthenticated(true);
        const biometricEnabled = await getBiometricPreference();
        setBiometricEnabled(biometricEnabled);
      } catch {
        await clearTokens();
      }
    } catch {
      await clearTokens();
    } finally {
      setLoading(false);
    }
  };

  /**
   * Logout: deactivate push token, fire-and-forget backend call, clear all local state.
   */
  const logout = async () => {
    // Deactivate push token on logout
    deactivatePushToken().catch(() => {});

    try {
      authApi.logout().catch(() => {}); // fire-and-forget
    } catch {}

    await clearTokens();
    queryClient.clear();
    await storeLogout();
  };

  return { login, checkAuthOnLaunch, logout };
}
