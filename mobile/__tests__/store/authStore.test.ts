import { act } from 'react-test-renderer';
import { useAuthStore } from '../../src/store/authStore';

// Reset store between tests
beforeEach(() => {
  useAuthStore.setState({
    user: null,
    isAuthenticated: false,
    biometricEnabled: false,
    isLoading: true,
  });
});

describe('authStore', () => {
  it('setUser updates user state', () => {
    const mockUser = { id: '123', phone: '+919876543210', name: 'Test User', role: 'user' } as any;
    act(() => {
      useAuthStore.getState().setUser(mockUser);
    });
    expect(useAuthStore.getState().user).toEqual(mockUser);
  });

  it('setAuthenticated updates isAuthenticated', () => {
    act(() => {
      useAuthStore.getState().setAuthenticated(true);
    });
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('setBiometricEnabled updates biometricEnabled', () => {
    act(() => {
      useAuthStore.getState().setBiometricEnabled(true);
    });
    expect(useAuthStore.getState().biometricEnabled).toBe(true);
  });

  it('setLoading updates isLoading', () => {
    act(() => {
      useAuthStore.getState().setLoading(false);
    });
    expect(useAuthStore.getState().isLoading).toBe(false);
  });

  it('logout clears user and authentication', async () => {
    // Set some state first
    act(() => {
      useAuthStore.getState().setUser({ id: '1', phone: '+919876543210' } as any);
      useAuthStore.getState().setAuthenticated(true);
      useAuthStore.getState().setBiometricEnabled(true);
    });

    await act(async () => {
      await useAuthStore.getState().logout();
    });

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.biometricEnabled).toBe(false);
  });

  it('initial state is correct', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.biometricEnabled).toBe(false);
    expect(state.isLoading).toBe(true);
  });
});
