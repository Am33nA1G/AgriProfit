import { describe, it, expect, vi, beforeEach } from 'vitest';
import { authService } from '../auth';
import api from '@/lib/api';

// Mock the api module
vi.mock('@/lib/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe('Auth Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('requestOtp', () => {
    it('should send OTP request with phone number', async () => {
      const mockResponse = { data: { message: 'OTP sent' } };
      vi.mocked(api.post).mockResolvedValue(mockResponse);

      const result = await authService.requestOtp('9876543210');

      expect(api.post).toHaveBeenCalledWith('/auth/request-otp', {
        phone_number: '9876543210',
      });
      expect(result).toEqual({ message: 'OTP sent' });
    });

    it('should handle request OTP errors', async () => {
      vi.mocked(api.post).mockRejectedValue(new Error('Network error'));

      await expect(authService.requestOtp('9876543210')).rejects.toThrow('Network error');
    });
  });

  describe('verifyOtp', () => {
    it('should verify OTP and return auth response', async () => {
      const mockAuthResponse = {
        data: {
          access_token: 'test-token',
          user: { id: '1', phone_number: '9876543210', role: 'farmer' },
        },
      };
      vi.mocked(api.post).mockResolvedValue(mockAuthResponse);

      const result = await authService.verifyOtp('9876543210', '123456');

      expect(api.post).toHaveBeenCalledWith('/auth/verify-otp', {
        phone_number: '9876543210',
        otp: '123456',
      });
      expect(result).toEqual(mockAuthResponse.data);
    });

    it('should handle invalid OTP', async () => {
      vi.mocked(api.post).mockRejectedValue(new Error('Invalid OTP'));

      await expect(authService.verifyOtp('9876543210', '000000')).rejects.toThrow('Invalid OTP');
    });
  });

  describe('completeProfile', () => {
    it('should complete user profile', async () => {
      const profileData = {
        name: 'Test Farmer',
        district: 'Ernakulam',
        location: 'Kochi',
      };
      const mockUser = {
        data: {
          id: '1',
          name: 'Test Farmer',
          district: 'Ernakulam',
          role: 'farmer',
        },
      };
      vi.mocked(api.post).mockResolvedValue(mockUser);

      const result = await authService.completeProfile(profileData);

      expect(api.post).toHaveBeenCalledWith('/auth/complete-profile', profileData);
      expect(result).toEqual(mockUser.data);
    });
  });

  describe('getCurrentUser', () => {
    it('should fetch current user data', async () => {
      const mockUser = {
        data: {
          id: '1',
          phone_number: '9876543210',
          name: 'Test Farmer',
          role: 'farmer',
        },
      };
      vi.mocked(api.get).mockResolvedValue(mockUser);

      const result = await authService.getCurrentUser();

      expect(api.get).toHaveBeenCalledWith('/auth/me');
      expect(result).toEqual(mockUser.data);
    });

    it('should handle unauthorized error', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Unauthorized'));

      await expect(authService.getCurrentUser()).rejects.toThrow('Unauthorized');
    });
  });

  describe('logout', () => {
    it('should clear token and user from localStorage', () => {
      localStorage.setItem('token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ id: '1' }));

      authService.logout();

      expect(localStorage.getItem('token')).toBeNull();
      expect(localStorage.getItem('user')).toBeNull();
    });

    it('should work when no data in localStorage', () => {
      expect(() => authService.logout()).not.toThrow();
      expect(localStorage.getItem('token')).toBeNull();
    });
  });
});
