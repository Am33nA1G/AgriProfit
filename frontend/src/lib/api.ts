import axios from 'axios';
import { perfMonitor } from '@/utils/performance-monitor';

const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
    baseURL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 90000, // Increased to 90s for slow queries
});

export const apiWithLongTimeout = axios.create({
    baseURL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 60000,
});

api.interceptors.request.use((config) => {
    // Only access localStorage in browser environment
    if (typeof window !== 'undefined') {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    // Track request start time for performance monitoring
    (config as any)._startTime = performance.now();
    return config;
}, (error) => {
    return Promise.reject(error);
});

api.interceptors.response.use(
    (response) => {
        const startTime = (response.config as any)._startTime;
        if (startTime) {
            const duration = performance.now() - startTime;
            perfMonitor.recordAPI(response.config.url || '', duration, response.status);
        }
        return response;
    },
    (error) => {
        const startTime = error.config?._startTime;
        if (startTime) {
            const duration = performance.now() - startTime;
            perfMonitor.recordAPI(error.config?.url || '', duration, error.response?.status || 0);
        }

        if (error.response?.status === 401 && typeof window !== 'undefined') {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default api;