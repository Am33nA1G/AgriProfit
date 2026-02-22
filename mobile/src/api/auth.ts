import apiClient from './client';
import type { AuthTokens, OTPRequest, OTPVerify } from '../types/api';
import type { User } from '../types/models';

export const authApi = {
  requestOTP: (phoneNumber: string) =>
    apiClient.post<{ message: string }>('/auth/request-otp', { phone_number: phoneNumber } as OTPRequest),

  verifyOTP: (phoneNumber: string, otp: string) =>
    apiClient.post<AuthTokens & { user: User }>('/auth/verify-otp', {
      phone_number: phoneNumber,
      otp,
    } as OTPVerify),

  completeProfile: (data: { name: string; state: string; district: string }) =>
    apiClient.post<User>('/auth/complete-profile', data),

  refreshToken: (refreshToken: string) =>
    apiClient.post<AuthTokens>('/auth/refresh', { refresh_token: refreshToken }),

  logout: () => apiClient.post<void>('/auth/logout'),

  getCurrentUser: () => apiClient.get<User>('/auth/me'),
};
