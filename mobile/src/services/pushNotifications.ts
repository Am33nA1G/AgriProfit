import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { notificationsApi } from '../api/notifications';

const PUSH_TOKEN_KEY = 'expo_push_token';

/**
 * Request permissions and register Expo push token with the backend.
 */
export async function registerForPushNotifications(): Promise<string | null> {
  if (!Device.isDevice) {
    console.warn('Push notifications only work on physical devices');
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    return null;
  }

  // Configure Android notification channel
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'AgriProfit',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#16a34a',
    });
  }

  const projectId = Constants.expoConfig?.extra?.eas?.projectId;
  const tokenData = await Notifications.getExpoPushTokenAsync({ projectId });
  const token = tokenData.data;

  // Store locally in SecureStore
  await SecureStore.setItemAsync(PUSH_TOKEN_KEY, token);

  // Register with backend
  try {
    await notificationsApi.registerPushToken(
      token,
      Platform.OS === 'ios' ? 'ios' : 'android',
      Device.modelName ?? undefined,
      Constants.expoConfig?.version ?? undefined,
    );
  } catch (err) {
    console.warn('Failed to register push token with backend:', err);
  }

  return token;
}

/**
 * Deactivate push token on logout.
 */
export async function deactivatePushToken(): Promise<void> {
  const token = await SecureStore.getItemAsync(PUSH_TOKEN_KEY);
  if (!token) return;
  try {
    await notificationsApi.deactivatePushToken(token);
    await SecureStore.deleteItemAsync(PUSH_TOKEN_KEY);
  } catch {
    // Best-effort
  }
}

/**
 * Set up notification handlers for foreground/background/tap.
 */
export function setupNotificationHandlers(
  onNotificationPress: (data: Record<string, string>) => void,
): () => void {
  // Foreground: show as in-app notification (don't show OS notification banner)
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: false, // suppress OS banner in foreground
      shouldPlaySound: false,
      shouldSetBadge: true,
    }),
  });

  // Tap on notification from background/killed state
  const sub = Notifications.addNotificationResponseReceivedListener(response => {
    const data = response.notification.request.content.data as Record<string, string>;
    onNotificationPress(data);
  });

  return () => sub.remove();
}
