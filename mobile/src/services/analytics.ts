import { AppState, AppStateStatus } from 'react-native';
import * as Sentry from '@sentry/react-native';
import { mmkv } from './mmkvStorage';

const ANALYTICS_BUFFER_KEY = '__analytics-buffer__';
const MAX_BUFFER_SIZE = 100;
const FLUSH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

interface AnalyticsEvent {
  category: string;
  message: string;
  data?: Record<string, unknown>;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Buffer helpers
// ---------------------------------------------------------------------------

function readBuffer(): AnalyticsEvent[] {
  try {
    const raw = mmkv.getString(ANALYTICS_BUFFER_KEY);
    return raw ? (JSON.parse(raw) as AnalyticsEvent[]) : [];
  } catch {
    return [];
  }
}

function writeBuffer(events: AnalyticsEvent[]): void {
  mmkv.set(ANALYTICS_BUFFER_KEY, JSON.stringify(events));
}

function bufferEvent(
  category: string,
  message: string,
  data?: Record<string, unknown>,
): void {
  const events = readBuffer();
  events.push({ category, message, data, timestamp: new Date().toISOString() });
  if (events.length > MAX_BUFFER_SIZE) {
    events.splice(0, events.length - MAX_BUFFER_SIZE);
  }
  writeBuffer(events);
}

// ---------------------------------------------------------------------------
// Flush
// ---------------------------------------------------------------------------

/**
 * Flush buffered events to Sentry breadcrumbs and clear the buffer.
 */
export function flushEvents(): void {
  const events = readBuffer();
  if (events.length === 0) return;
  for (const event of events) {
    Sentry.addBreadcrumb({
      category: event.category,
      message: event.message,
      data: { ...event.data, buffered_at: event.timestamp },
      level: 'info',
    });
  }
  writeBuffer([]);
}

let _flushInterval: ReturnType<typeof setInterval> | null = null;

/**
 * Start the periodic flush interval and background flush listener.
 * Returns a cleanup function — call it on app unmount.
 */
export function startAnalyticsFlush(): () => void {
  // Clear existing interval if any
  if (_flushInterval !== null) {
    clearInterval(_flushInterval);
  }

  _flushInterval = setInterval(flushEvents, FLUSH_INTERVAL_MS);

  const subscription = AppState.addEventListener('change', (state: AppStateStatus) => {
    if (state === 'background' || state === 'inactive') {
      flushEvents();
    }
  });

  return () => {
    if (_flushInterval !== null) {
      clearInterval(_flushInterval);
      _flushInterval = null;
    }
    subscription.remove();
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Initialize Sentry for crash reporting and performance monitoring.
 * Should be called as early as possible in the app lifecycle.
 */
export function initSentry(): void {
  const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN;
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: process.env.EXPO_PUBLIC_ENV ?? 'development',
    tracesSampleRate: process.env.EXPO_PUBLIC_ENV === 'production' ? 0.2 : 1.0,
    profilesSampleRate: process.env.EXPO_PUBLIC_ENV === 'production' ? 0.1 : 0,
    enableAutoSessionTracking: true,
    sessionTrackingIntervalMillis: 30000,
    attachScreenshot: true,
    maxBreadcrumbs: process.env.EXPO_PUBLIC_ENV === 'production' ? 100 : 20,
  });
}

/**
 * Identify the current user in Sentry.
 */
export function identifyUser(id: string, phone: string): void {
  Sentry.setUser({ id, username: phone });
}

/**
 * Clear user identity (called on logout).
 */
export function clearUser(): void {
  Sentry.setUser(null);
}

/**
 * Capture a non-fatal error with optional context.
 */
export function captureError(error: Error, context?: Record<string, unknown>): void {
  Sentry.withScope(scope => {
    if (context) scope.setExtras(context);
    Sentry.captureException(error);
  });
}

/**
 * Track a screen view. Adds a navigation breadcrumb and buffers the event.
 */
export function trackScreen(screenName: string): void {
  Sentry.addBreadcrumb({
    category: 'navigation',
    message: `Screen: ${screenName}`,
    level: 'info',
  });
  bufferEvent('navigation', `Screen: ${screenName}`, { screenName });
}

/**
 * Track a feature usage event. Buffers the event for periodic flush to Sentry.
 */
export function trackEvent(
  category: string,
  message: string,
  data?: Record<string, unknown>,
): void {
  bufferEvent(category, message, data);
}
