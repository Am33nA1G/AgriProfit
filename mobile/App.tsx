import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import { QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import * as Sentry from '@sentry/react-native';
import { queryClient } from './src/api/queryClient';
import { useAuthStore } from './src/store/authStore';
import { useNetworkStore } from './src/store/networkStore';
import { useAuth } from './src/hooks/useAuth';
import { initSentry } from './src/services/analytics';
import RootNavigator from './src/navigation/RootNavigator';
import OfflineBanner from './src/components/layout/OfflineBanner';
import SyncStatus from './src/components/ui/SyncStatus';
import { ErrorBoundary } from './src/components/ErrorBoundary';
import LoadingSpinner from './src/components/ui/LoadingSpinner';
import './src/i18n'; // initialize i18n

// Initialize Sentry early
initSentry();

function AppContent() {
  const isLoading = useAuthStore(s => s.isLoading);
  const initNetwork = useNetworkStore(s => s.initialize);
  const { checkAuthOnLaunch } = useAuth();

  useEffect(() => {
    const unsubscribe = initNetwork();

    // Use the hook's auth check which includes token refresh logic
    checkAuthOnLaunch();

    return unsubscribe;
  }, []);

  if (isLoading) {
    return <LoadingSpinner fullScreen />;
  }

  return (
    <View style={styles.container}>
      <OfflineBanner />
      <SyncStatus />
      <RootNavigator />
      <StatusBar style="auto" />
    </View>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppContent />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default Sentry.wrap(App);

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});
