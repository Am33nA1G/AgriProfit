// App.tsx — AgriProfit Mobile root entry point.
// react-native-gesture-handler MUST be imported first.

import 'react-native-gesture-handler';
import React from 'react';
import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import Toast from 'react-native-toast-message';
import { ErrorBoundary } from './src/components/ErrorBoundary';
import { QueryProvider } from './src/providers/QueryProvider';
import { RootNavigator } from './src/navigation/RootNavigator';

export default function App() {
    return (
        <ErrorBoundary>
            <QueryProvider>
                <SafeAreaProvider>
                    <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
                    <RootNavigator />
                    <Toast />
                </SafeAreaProvider>
            </QueryProvider>
        </ErrorBoundary>
    );
}
