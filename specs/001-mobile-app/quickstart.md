# Quickstart: AgriProfit Mobile App

**Branch**: `001-mobile-app` | **Date**: 2026-02-21

## Prerequisites

- Node.js 20+
- Expo CLI (`npm install -g expo-cli` or use `npx expo`)
- EAS CLI (`npm install -g eas-cli`)
- Android Studio (for Android emulator) or physical device
- Xcode 15+ (for iOS simulator, macOS only)
- Backend running locally on port 8000

## Initial Setup

```bash
# From repo root
npx create-expo-app mobile --template expo-template-blank-typescript
cd mobile

# Core dependencies
npx expo install expo-secure-store expo-local-authentication expo-notifications
npx expo install expo-constants expo-device expo-linking expo-status-bar
npx expo install @react-native-community/netinfo react-native-mmkv

# Navigation
npm install @react-navigation/native @react-navigation/bottom-tabs @react-navigation/native-stack
npx expo install react-native-screens react-native-safe-area-context

# State & Data
npm install zustand @tanstack/react-query axios

# UI
npm install react-native-svg react-native-gifted-charts
npx expo install react-native-gesture-handler react-native-reanimated

# i18n
npm install i18next react-i18next

# Observability
npx expo install @sentry/react-native

# Dev dependencies
npm install -D typescript @types/react jest @testing-library/react-native
```

## Environment Configuration

Create `mobile/.env`:
```
EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1
EXPO_PUBLIC_SENTRY_DSN=<your-sentry-dsn>
EXPO_PUBLIC_ENV=development
```

## Project Structure

```
mobile/
├── app.json                    # Expo config
├── eas.json                    # EAS build profiles
├── App.tsx                     # Entry point
├── src/
│   ├── api/
│   │   ├── client.ts           # Axios instance + interceptors
│   │   ├── auth.ts             # Auth API calls
│   │   ├── commodities.ts      # Commodity API calls
│   │   ├── prices.ts           # Price API calls
│   │   ├── mandis.ts           # Mandi API calls
│   │   ├── transport.ts        # Transport API calls
│   │   ├── inventory.ts        # Inventory API calls
│   │   ├── sales.ts            # Sales API calls
│   │   ├── community.ts        # Community API calls
│   │   ├── notifications.ts    # Notification API calls
│   │   └── admin.ts            # Admin API calls
│   ├── components/
│   │   ├── ui/                 # Shared UI components (Button, Card, Input, etc.)
│   │   ├── charts/             # Chart wrappers (PriceChart, TrendLine, etc.)
│   │   ├── layout/             # Layout components (Screen, Header, TabBar)
│   │   └── forms/              # Form components (OTPInput, SearchBar, etc.)
│   ├── hooks/
│   │   ├── useAuth.ts          # Auth state + actions
│   │   ├── useBiometric.ts     # Biometric availability + prompt
│   │   ├── useNetwork.ts       # Connectivity status
│   │   ├── useOfflineQueue.ts  # Queue operations
│   │   └── queries/            # React Query hooks per domain
│   │       ├── useCommodities.ts
│   │       ├── usePrices.ts
│   │       ├── useInventory.ts
│   │       ├── useSales.ts
│   │       ├── useCommunity.ts
│   │       └── useNotifications.ts
│   ├── navigation/
│   │   ├── RootNavigator.tsx   # Auth check → AuthStack or MainTabs
│   │   ├── AuthStack.tsx       # Login → OTP → PIN Setup
│   │   ├── MainTabs.tsx        # Bottom tab navigator
│   │   ├── PricesStack.tsx     # Prices → CommodityDetail → MandiDetail
│   │   ├── CommunityStack.tsx  # Posts → PostDetail → CreatePost
│   │   └── types.ts            # Navigation param types
│   ├── screens/
│   │   ├── auth/               # LoginScreen, OTPScreen, PINSetupScreen
│   │   ├── dashboard/          # DashboardScreen
│   │   ├── prices/             # CommodityListScreen, CommodityDetailScreen
│   │   ├── transport/          # TransportScreen, ComparisonScreen
│   │   ├── inventory/          # InventoryScreen, AddInventoryScreen
│   │   ├── sales/              # SalesScreen, AddSaleScreen, AnalyticsScreen
│   │   ├── community/          # PostsScreen, PostDetailScreen, CreatePostScreen
│   │   ├── notifications/      # NotificationsScreen
│   │   ├── admin/              # AdminDashboard, BroadcastScreen
│   │   └── profile/            # ProfileScreen, SettingsScreen
│   ├── store/
│   │   ├── authStore.ts        # Zustand: auth state
│   │   ├── networkStore.ts     # Zustand: connectivity
│   │   ├── offlineQueueStore.ts # Zustand: queue state
│   │   └── settingsStore.ts    # Zustand: language, theme
│   ├── services/
│   │   ├── secureStorage.ts    # SecureStore wrapper
│   │   ├── offlineQueue.ts     # Queue engine (MMKV)
│   │   ├── pushNotifications.ts # Expo push registration
│   │   ├── biometric.ts        # Biometric/PIN auth
│   │   ├── analytics.ts        # Event tracking
│   │   └── sentry.ts           # Crash reporting setup
│   ├── i18n/
│   │   ├── index.ts            # i18next config
│   │   ├── en.json             # English strings
│   │   └── hi.json             # Hindi strings
│   ├── theme/
│   │   ├── colors.ts           # Color palette (matches web)
│   │   ├── typography.ts       # Font sizes, weights
│   │   └── spacing.ts          # Spacing scale
│   ├── utils/
│   │   ├── formatting.ts       # Price formatting, date formatting
│   │   ├── validation.ts       # Phone number, OTP validation
│   │   └── constants.ts        # App constants
│   └── types/
│       ├── api.ts              # API response types
│       ├── navigation.ts       # Navigation param types
│       └── models.ts           # Domain model types
├── __tests__/
│   ├── api/                    # API client tests
│   ├── hooks/                  # Hook tests
│   ├── screens/                # Screen tests
│   ├── services/               # Service tests
│   └── store/                  # Store tests
└── assets/
    ├── images/
    └── fonts/
```

## Running Locally

```bash
# Terminal 1: Backend
cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0

# Terminal 2: Mobile
cd mobile && npx expo start

# Press 'a' for Android emulator, 'i' for iOS simulator
# Or scan QR code with Expo Go on physical device
```

## Key Configuration Files

### app.json
```json
{
  "expo": {
    "name": "AgriProfit",
    "slug": "agriprofit",
    "version": "1.0.0",
    "sdkVersion": "52.0.0",
    "platforms": ["ios", "android"],
    "ios": {
      "bundleIdentifier": "com.agriprofit.mobile",
      "supportsTablet": false,
      "infoPlist": {
        "NSFaceIDUsageDescription": "Use Face ID to unlock the app"
      }
    },
    "android": {
      "package": "com.agriprofit.mobile",
      "adaptiveIcon": { "foregroundImage": "./assets/adaptive-icon.png" },
      "permissions": ["RECEIVE_BOOT_COMPLETED", "VIBRATE"]
    },
    "plugins": [
      "@sentry/react-native/expo",
      ["expo-notifications", { "icon": "./assets/notification-icon.png" }],
      "expo-secure-store",
      "expo-local-authentication"
    ]
  }
}
```

### eas.json
```json
{
  "cli": { "version": ">= 12.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "env": { "EXPO_PUBLIC_API_URL": "http://localhost:8000/api/v1" }
    },
    "preview": {
      "distribution": "internal",
      "env": { "EXPO_PUBLIC_API_URL": "https://staging.agriprofit.in/api/v1" }
    },
    "production": {
      "env": { "EXPO_PUBLIC_API_URL": "https://api.agriprofit.in/api/v1" }
    }
  },
  "submit": {
    "production": {
      "ios": { "appleId": "your-apple-id", "ascAppId": "your-app-id" },
      "android": { "serviceAccountKeyPath": "./google-services.json" }
    }
  }
}
```

## Example: API Client with Auth Interceptor

```typescript
// src/api/client.ts
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { useAuthStore } from '../store/authStore';

const API_URL = process.env.EXPO_PUBLIC_API_URL;

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 15000, // 15s timeout for slow 3G
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token
apiClient.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 → silent refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = await SecureStore.getItemAsync('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          await SecureStore.setItemAsync('access_token', data.access_token);
          if (data.refresh_token) {
            await SecureStore.setItemAsync('refresh_token', data.refresh_token);
          }
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return apiClient(originalRequest);
        } catch {
          useAuthStore.getState().logout();
        }
      }
    }
    // Handle 429 rate limit
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'] || 5;
      await new Promise((r) => setTimeout(r, retryAfter * 1000));
      return apiClient(originalRequest);
    }
    return Promise.reject(error);
  }
);
```

## Example: Biometric Restore Flow

```typescript
// src/services/biometric.ts
import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';

export async function checkBiometricAvailability() {
  const compatible = await LocalAuthentication.hasHardwareAsync();
  const enrolled = await LocalAuthentication.isEnrolledAsync();
  return { compatible, enrolled, available: compatible && enrolled };
}

export async function authenticateWithBiometric(): Promise<boolean> {
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: 'Unlock AgriProfit',
    fallbackLabel: 'Use PIN',
    cancelLabel: 'Cancel',
    disableDeviceFallback: true, // We handle PIN ourselves
  });
  return result.success;
}

export async function restoreSession(): Promise<boolean> {
  // Try biometric first
  const { available } = await checkBiometricAvailability();
  if (available) {
    const success = await authenticateWithBiometric();
    if (success) {
      const refreshToken = await SecureStore.getItemAsync('refresh_token');
      if (refreshToken) {
        // Use stored refresh token to get new access token
        return true;
      }
    }
  }
  // Biometric failed or unavailable — fall through to PIN
  return false;
}
```
