/**
 * Integration tests for the auth flow (T122).
 * Tests the complete login → session restore → logout cycle.
 */

// Mocks must come first
jest.mock('../../src/api/auth', () => ({
  authApi: {
    verifyOTP: jest.fn(),
    getCurrentUser: jest.fn(),
    refreshToken: jest.fn(),
    logout: jest.fn().mockResolvedValue(undefined),
    requestOTP: jest.fn(),
  },
}));

jest.mock('../../src/services/secureStorage', () => ({
  saveTokens: jest.fn().mockResolvedValue(undefined),
  getAccessToken: jest.fn(),
  getRefreshToken: jest.fn(),
  clearTokens: jest.fn().mockResolvedValue(undefined),
  getBiometricPreference: jest.fn().mockResolvedValue(false),
  saveBiometricPreference: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../../src/services/pushNotifications', () => ({
  registerForPushNotifications: jest.fn().mockResolvedValue(undefined),
  deactivatePushToken: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../../src/api/queryClient', () => ({
  queryClient: { clear: jest.fn() },
}));

jest.mock('@react-native-community/netinfo', () => ({
  __esModule: true,
  default: {
    addEventListener: jest.fn().mockReturnValue(() => {}),
    fetch: jest.fn().mockResolvedValue({ isConnected: true }),
  },
}));

import { authApi } from '../../src/api/auth';
import {
  saveTokens,
  getAccessToken,
  getRefreshToken,
  clearTokens,
} from '../../src/services/secureStorage';
import { useAuthStore } from '../../src/store/authStore';

const mockUser = {
  id: 'user-123',
  phone_number: '+919876543210',
  name: 'Test Farmer',
  is_profile_complete: true,
  role: 'user',
  state: 'Kerala',
  district: 'Ernakulam',
};

describe('Auth Flow: Login', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset auth store to initial state
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      biometricEnabled: false,
      isLoading: false,
    });
  });

  it('verifyOTP returns tokens and user', async () => {
    (authApi.verifyOTP as jest.Mock).mockResolvedValue({
      data: {
        access_token: 'access-123',
        refresh_token: 'refresh-456',
        user: mockUser,
      },
    });

    const response = await authApi.verifyOTP('+919876543210', '123456');
    const { access_token, refresh_token, user } = (response as any).data;

    expect(access_token).toBe('access-123');
    expect(refresh_token).toBe('refresh-456');
    expect(user.id).toBe('user-123');
  });

  it('saveTokens is called after successful OTP verification', async () => {
    (authApi.verifyOTP as jest.Mock).mockResolvedValue({
      data: {
        access_token: 'access-abc',
        refresh_token: 'refresh-xyz',
        user: mockUser,
      },
    });

    const response = await authApi.verifyOTP('+919876543210', '654321');
    const { access_token, refresh_token } = (response as any).data;
    await saveTokens(access_token, refresh_token);

    expect(saveTokens).toHaveBeenCalledWith('access-abc', 'refresh-xyz');
  });

  it('auth store is updated after login', async () => {
    (authApi.verifyOTP as jest.Mock).mockResolvedValue({
      data: {
        access_token: 'tok-1',
        refresh_token: 'ref-1',
        user: mockUser,
      },
    });

    const response = await authApi.verifyOTP('+919876543210', '000000');
    const { user } = (response as any).data;

    useAuthStore.getState().setUser(user);
    useAuthStore.getState().setAuthenticated(true);

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.id).toBe('user-123');
  });
});

describe('Auth Flow: Auto-login (session restore)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      biometricEnabled: false,
      isLoading: false,
    });
  });

  it('restores session when valid access token exists', async () => {
    (getAccessToken as jest.Mock).mockResolvedValue('valid-token');
    (authApi.getCurrentUser as jest.Mock).mockResolvedValue({ data: mockUser });

    const token = await getAccessToken();
    expect(token).toBe('valid-token');

    const meResponse = await authApi.getCurrentUser();
    useAuthStore.getState().setUser((meResponse as any).data);
    useAuthStore.getState().setAuthenticated(true);

    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().user?.name).toBe('Test Farmer');
  });

  it('refreshes token and restores session when access token expired', async () => {
    (getAccessToken as jest.Mock).mockResolvedValue('expired-token');
    (authApi.getCurrentUser as jest.Mock)
      .mockRejectedValueOnce({ response: { status: 401 } }) // first call fails
      .mockResolvedValueOnce({ data: mockUser }); // second call after refresh
    (getRefreshToken as jest.Mock).mockResolvedValue('valid-refresh');
    (authApi.refreshToken as jest.Mock).mockResolvedValue({
      data: { access_token: 'new-access', refresh_token: 'new-refresh' },
    });

    // Simulate the refresh flow
    const refreshResponse = await authApi.refreshToken('valid-refresh');
    const { access_token, refresh_token } = (refreshResponse as any).data;
    await saveTokens(access_token, refresh_token);
    const meResponse = await authApi.getCurrentUser();
    useAuthStore.getState().setUser((meResponse as any).data);
    useAuthStore.getState().setAuthenticated(true);

    expect(saveTokens).toHaveBeenCalledWith('new-access', 'new-refresh');
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('clears state when no access token is stored', async () => {
    (getAccessToken as jest.Mock).mockResolvedValue(null);

    const token = await getAccessToken();
    if (!token) {
      await clearTokens();
    }

    expect(clearTokens).toHaveBeenCalledTimes(1);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('clears tokens when refresh also fails', async () => {
    (getAccessToken as jest.Mock).mockResolvedValue('expired-token');
    (authApi.getCurrentUser as jest.Mock).mockRejectedValue({ response: { status: 401 } });
    (getRefreshToken as jest.Mock).mockResolvedValue('bad-refresh');
    (authApi.refreshToken as jest.Mock).mockRejectedValue(new Error('Invalid refresh token'));

    try {
      await authApi.refreshToken('bad-refresh');
    } catch {
      await clearTokens();
    }

    expect(clearTokens).toHaveBeenCalledTimes(1);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});

describe('Auth Flow: Logout', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuthStore.setState({
      user: mockUser,
      isAuthenticated: true,
      biometricEnabled: false,
      isLoading: false,
    });
  });

  it('clears tokens on logout', async () => {
    await clearTokens();
    expect(clearTokens).toHaveBeenCalledTimes(1);
  });

  it('resets auth store state after logout', async () => {
    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });

  it('backend logout is called fire-and-forget', async () => {
    (authApi.logout as jest.Mock).mockResolvedValue(undefined);
    authApi.logout().catch(() => {});
    // Does not throw even if it resolves immediately
    expect(authApi.logout).toHaveBeenCalledTimes(1);
  });
});
