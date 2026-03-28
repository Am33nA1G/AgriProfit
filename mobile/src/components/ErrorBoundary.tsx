// mobile/src/components/ErrorBoundary.tsx
// UX-07: Global React Native error boundary at app root.
// IMPORTANT: Uses plain system styles (no tokens import) — tokens could be the crash source.

import React, { Component, type ReactNode, type ErrorInfo } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    ScrollView,
    Platform,
} from 'react-native';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        this.setState({ errorInfo });
        if (__DEV__) {
            console.error('[ErrorBoundary] Caught error:', error);
            console.error('[ErrorBoundary] Stack:', errorInfo.componentStack);
        }
    }

    handleRestart = () => {
        // In Expo managed workflow, DevSettings.reload() works in dev
        // In production, expo-updates reloadAsync would be used here
        this.setState({ hasError: false, error: null, errorInfo: null });
    };

    render() {
        if (!this.state.hasError) {
            return this.props.children;
        }

        return (
            <ScrollView
                style={styles.scrollView}
                contentContainerStyle={styles.container}
            >
                <View style={styles.iconContainer}>
                    <Text style={styles.iconText}>⚠️</Text>
                </View>

                <Text style={styles.title}>Something went wrong</Text>
                <Text style={styles.subtitle}>
                    The app encountered an unexpected error.
                </Text>

                {/* Stack trace — dev only (UX-07) */}
                {__DEV__ && this.state.error && (
                    <View style={styles.errorBox}>
                        <Text style={styles.errorTitle}>Error (dev only)</Text>
                        <Text style={styles.errorMessage}>{this.state.error.message}</Text>
                        {this.state.errorInfo?.componentStack ? (
                            <Text style={styles.errorStack}>
                                {this.state.errorInfo.componentStack}
                            </Text>
                        ) : null}
                    </View>
                )}

                <TouchableOpacity
                    style={styles.primaryButton}
                    onPress={this.handleRestart}
                    activeOpacity={0.8}
                >
                    <Text style={styles.primaryButtonText}>Try to Continue</Text>
                </TouchableOpacity>
            </ScrollView>
        );
    }
}

// Plain system styles — intentionally NOT importing from tokens.ts
const styles = StyleSheet.create({
    scrollView: { flex: 1, backgroundColor: '#ffffff' },
    container: {
        flexGrow: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 32,
        paddingVertical: 48,
    },
    iconContainer: { marginBottom: 16 },
    iconText: { fontSize: 64, textAlign: 'center' },
    title: {
        fontSize: 22,
        fontWeight: '700',
        color: '#111827',
        textAlign: 'center',
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 15,
        color: '#6b7280',
        textAlign: 'center',
        marginBottom: 32,
        lineHeight: 22,
    },
    errorBox: {
        width: '100%',
        backgroundColor: '#fef2f2',
        borderColor: '#fca5a5',
        borderWidth: 1,
        borderRadius: 8,
        padding: 12,
        marginBottom: 24,
    },
    errorTitle: {
        fontSize: 12,
        fontWeight: '700',
        color: '#b91c1c',
        marginBottom: 4,
        textTransform: 'uppercase',
    },
    errorMessage: {
        fontSize: 13,
        color: '#7f1d1d',
        fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
        marginBottom: 8,
    },
    errorStack: {
        fontSize: 11,
        color: '#9ca3af',
        fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    },
    primaryButton: {
        width: '100%',
        backgroundColor: '#16a34a',
        borderRadius: 12,
        paddingVertical: 14,
        alignItems: 'center',
    },
    primaryButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: '#ffffff',
    },
});
