import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from 'axios';
import * as Sentry from '@sentry/react-native';
import { getAccessToken, getRefreshToken, saveTokens, clearTokens } from '../services/secureStorage';
import { API_TIMEOUT, MAX_RETRY } from '../utils/constants';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach Bearer token + start perf span
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig & { _sentrySpanStart?: number }) => {
    const token = await getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    config._sentrySpanStart = Date.now();
    return config;
  },
  error => Promise.reject(error),
);

// Track if we're currently refreshing to avoid multiple refresh calls
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function onRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
}

// Response interceptor: handle 401 (token refresh) and 429 (rate limit) + record perf
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const config = response.config as InternalAxiosRequestConfig & { _sentrySpanStart?: number };
    if (config._sentrySpanStart) {
      const durationMs = Date.now() - config._sentrySpanStart;
      Sentry.addBreadcrumb({
        category: 'http',
        message: `${config.method?.toUpperCase()} ${config.url} — ${durationMs}ms`,
        data: { status: response.status, duration_ms: durationMs },
        level: 'info',
      });
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
      _retryCount?: number;
    };

    // 401 — Token expired, try to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue requests while refresh is in progress
        return new Promise(resolve => {
          refreshSubscribers.push((token: string) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            resolve(apiClient(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = await getRefreshToken();
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await axios.post(`${API_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;
        await saveTokens(access_token, newRefreshToken);
        onRefreshed(access_token);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        await clearTokens();
        // authStore.logout() will be called from the component layer
        return Promise.reject(refreshError); // Return refresh error, not original
      } finally {
        isRefreshing = false;
      }
    }

    // 429 — Rate limited, retry with exponential backoff
    if (error.response?.status === 429) {
      originalRequest._retryCount = (originalRequest._retryCount ?? 0) + 1;

      if (originalRequest._retryCount <= MAX_RETRY) {
        const retryAfterHeader = error.response.headers['retry-after'];
        const retryAfterMs = retryAfterHeader
          ? parseInt(retryAfterHeader, 10) * 1000
          : Math.pow(2, originalRequest._retryCount) * 1000;

        await new Promise(resolve => setTimeout(resolve, retryAfterMs));
        return apiClient(originalRequest);
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
