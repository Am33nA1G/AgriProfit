import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
  Animated,
} from 'react-native';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

interface RateLimitBannerProps {
  /** Whether a rate-limited request is currently being retried */
  isRetrying: boolean;
  /** Whether all retries have been exhausted */
  maxRetriesExceeded?: boolean;
  /** Called when user taps "Try Again" */
  onRetry?: () => void;
}

export default function RateLimitBanner({
  isRetrying,
  maxRetriesExceeded,
  onRetry,
}: RateLimitBannerProps) {
  const [opacity] = useState(new Animated.Value(0));

  useEffect(() => {
    if (isRetrying || maxRetriesExceeded) {
      Animated.timing(opacity, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }).start();
    } else {
      Animated.timing(opacity, {
        toValue: 0,
        duration: 200,
        useNativeDriver: true,
      }).start();
    }
  }, [isRetrying, maxRetriesExceeded]);

  if (!isRetrying && !maxRetriesExceeded) return null;

  return (
    <Animated.View style={[styles.banner, { opacity }]}>
      {maxRetriesExceeded ? (
        <View style={styles.row}>
          <Text style={styles.text}>⚠️ Service is busy. Please try again in a few minutes.</Text>
          {onRetry && (
            <TouchableOpacity style={styles.retryBtn} onPress={onRetry}>
              <Text style={styles.retryText}>Retry</Text>
            </TouchableOpacity>
          )}
        </View>
      ) : (
        <View style={styles.row}>
          <ActivityIndicator size="small" color="#fff" style={styles.spinner} />
          <Text style={styles.text}>Fetching data, please wait...</Text>
        </View>
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  banner: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: colors.warning,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    zIndex: 999,
  },
  row: { flexDirection: 'row', alignItems: 'center' },
  spinner: { marginRight: spacing[2] },
  text: {
    flex: 1,
    color: '#fff',
    fontSize: typography.fontSize.xs,
    fontWeight: typography.fontWeight.medium,
  },
  retryBtn: {
    paddingHorizontal: spacing[3],
    paddingVertical: 4,
    backgroundColor: 'rgba(255,255,255,0.25)',
    borderRadius: 4,
  },
  retryText: { color: '#fff', fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold },
});
