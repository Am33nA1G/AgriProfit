import api from '@/lib/api';
import { AuthResponse, ProfileData, User } from '@/types';

export const authService = {
    requestOtp: async (phoneNumber: string) => {
        const response = await api.post('/auth/request-otp', {
            phone_number: phoneNumber
        });
        return response.data;
    },

    verifyOtp: async (phoneNumber: string, otp: string): Promise<AuthResponse> => {
        const response = await api.post('/auth/verify-otp', {
            phone_number: phoneNumber,
            otp
        });
        return response.data;
    },

    completeProfile: async (profileData: ProfileData): Promise<User> => {
        const response = await api.post('/auth/complete-profile', profileData);
        return response.data;
    },

    getCurrentUser: async (): Promise<User> => {
        const response = await api.get('/auth/me');
        return response.data;
    },

    logout: () => {
        if (typeof window !== 'undefined') {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
        }
    },
};