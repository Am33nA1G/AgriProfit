import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { LineChart } from 'react-native-gifted-charts';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

const MAX_DATA_POINTS = 30;

export interface PricePoint {
  date: string;
  price: number;
}

interface PriceChartProps {
  priceHistory: PricePoint[];
  days: 7 | 30;
}

export default function PriceChart({ priceHistory, days }: PriceChartProps) {
  const chartData = useMemo(() => {
    if (!priceHistory?.length) return [];

    // Sort by date ascending
    const sorted = [...priceHistory].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
    );

    // Take last N days
    const recent = sorted.slice(-days);

    // Sample down to MAX_DATA_POINTS for performance on low-end devices
    const sampleEvery = recent.length > MAX_DATA_POINTS
      ? Math.ceil(recent.length / MAX_DATA_POINTS)
      : 1;

    const sampled = recent.filter((_, i) => i % sampleEvery === 0);

    return sampled.map(record => ({
      value: record.price,
      label: new Date(record.date).toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
      }),
    }));
  }, [priceHistory, days]);

  if (!chartData.length) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>No price data available</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <LineChart
        data={chartData}
        width={320}
        height={180}
        color={colors.primary[600]}
        thickness={2}
        dataPointsColor={colors.primary[700]}
        dataPointsRadius={chartData.length > 15 ? 0 : 3}
        startFillColor={colors.primary[100]}
        endFillColor={colors.background}
        areaChart
        curved
        hideDataPoints={chartData.length > 15}
        yAxisTextStyle={{ color: colors.text.secondary, fontSize: 10 }}
        xAxisLabelTextStyle={{ color: colors.text.secondary, fontSize: 9 }}
        noOfSections={4}
        formatYLabel={(val: string) => `₹${parseInt(val, 10).toLocaleString('en-IN')}`}
        showVerticalLines
        verticalLinesColor={colors.border}
        rulesColor={colors.border}
        backgroundColor={colors.background}
        // Disable animations for better performance on low-end devices
        isAnimated={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    paddingVertical: spacing[2],
  },
  empty: {
    height: 160,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
  },
});
