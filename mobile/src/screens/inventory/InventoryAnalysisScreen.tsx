// mobile/src/screens/inventory/InventoryAnalysisScreen.tsx
// Analyze the farmer's inventory: value breakdown, per-crop stats, and key insights.
// Reads from inventoryStore — no backend dependency required.

import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { BarChart } from 'react-native-gifted-charts';
import { TrendingUp, Package, Award, Layers } from 'lucide-react-native';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import { useInventoryStore } from '../../store/inventoryStore';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function itemValue(quantity: string, pricePerUnit: string): number {
    return (parseFloat(quantity) || 0) * (parseFloat(pricePerUnit) || 0);
}

function itemQuantityKg(quantity: string, unit: string): number {
    const q = parseFloat(quantity) || 0;
    if (unit === 'quintal') return q * 100;
    if (unit === 'ton') return q * 1000;
    return q; // kg and piece treated as-is
}

// ─── Screen ───────────────────────────────────────────────────────────────────

export function InventoryAnalysisScreen() {
    const { items } = useInventoryStore();

    if (items.length === 0) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.emptyState}>
                    <Layers size={48} color={colors.muted} />
                    <Text style={styles.emptyTitle}>No inventory to analyze</Text>
                    <Text style={styles.emptySubtitle}>Add items in the Inventory tab to see insights</Text>
                </View>
            </SafeAreaView>
        );
    }

    // ── Derived analytics ────────────────────────────────────────────────────
    const totalValue = items.reduce((sum, it) => sum + itemValue(it.quantity, it.pricePerUnit), 0);
    const totalQuantityKg = items.reduce((sum, it) => sum + itemQuantityKg(it.quantity, it.unit), 0);

    const cropStats = items
        .map((it) => ({
            crop: it.crop,
            value: itemValue(it.quantity, it.pricePerUnit),
            quantityLabel: `${it.quantity} ${it.unit}`,
            sharePct: totalValue > 0 ? (itemValue(it.quantity, it.pricePerUnit) / totalValue) * 100 : 0,
        }))
        .sort((a, b) => b.value - a.value);

    const topCrop = cropStats[0];

    // Bar chart data — one bar per crop, value in ₹
    const chartData = cropStats.map((cs, i) => ({
        value: cs.value,
        label: cs.crop.length > 8 ? cs.crop.slice(0, 7) + '…' : cs.crop,
        frontColor: CHART_COLORS[i % CHART_COLORS.length],
    }));

    const avgPricePerKg =
        totalQuantityKg > 0
            ? items.reduce((sum, it) => {
                  const pricePerKg =
                      it.unit === 'quintal'
                          ? (parseFloat(it.pricePerUnit) || 0) / 100
                          : it.unit === 'ton'
                          ? (parseFloat(it.pricePerUnit) || 0) / 1000
                          : parseFloat(it.pricePerUnit) || 0;
                  return sum + pricePerKg * itemQuantityKg(it.quantity, it.unit);
              }, 0) / totalQuantityKg
            : 0;

    return (
        <SafeAreaView style={styles.safeArea}>
            <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
                {/* ── Summary Cards ──────────────────────────────────────── */}
                <View style={styles.summaryRow}>
                    <SummaryCard
                        icon={<TrendingUp size={18} color={colors.primary} />}
                        label="Total Value"
                        value={`₹${totalValue.toLocaleString('en-IN')}`}
                        highlight
                    />
                    <SummaryCard
                        icon={<Package size={18} color={colors.warning} />}
                        label="Total Stock"
                        value={`${totalQuantityKg.toLocaleString('en-IN')} kg`}
                    />
                </View>
                <View style={styles.summaryRow}>
                    <SummaryCard
                        icon={<Award size={18} color={colors.success} />}
                        label="Top Crop"
                        value={topCrop.crop}
                    />
                    <SummaryCard
                        icon={<Layers size={18} color={colors.chart3} />}
                        label="Avg Price / kg"
                        value={`₹${avgPricePerKg.toFixed(0)}`}
                    />
                </View>

                {/* ── Bar Chart ──────────────────────────────────────────── */}
                {items.length > 1 && (
                    <View style={styles.chartCard}>
                        <Text style={styles.sectionTitle}>Value by Crop</Text>
                        <Text style={styles.sectionSubtitle}>Estimated value (₹) per crop in inventory</Text>
                        <View style={styles.chartWrapper}>
                            <BarChart
                                data={chartData}
                                barWidth={36}
                                spacing={18}
                                height={160}
                                noOfSections={4}
                                yAxisTextStyle={styles.chartAxisText}
                                xAxisLabelTextStyle={styles.chartAxisText}
                                yAxisThickness={0}
                                xAxisThickness={1}
                                xAxisColor={colors.border}
                                hideRules
                                isAnimated
                            />
                        </View>
                    </View>
                )}

                {/* ── Per-crop Breakdown ─────────────────────────────────── */}
                <Text style={styles.sectionTitle}>Crop Breakdown</Text>
                <Text style={styles.sectionSubtitle}>Share of total inventory value</Text>

                {cropStats.map((cs, i) => (
                    <CropBreakdownRow
                        key={cs.crop}
                        rank={i + 1}
                        crop={cs.crop}
                        value={cs.value}
                        quantityLabel={cs.quantityLabel}
                        sharePct={cs.sharePct}
                        color={CHART_COLORS[i % CHART_COLORS.length]}
                    />
                ))}

                {/* ── Key Insight ────────────────────────────────────────── */}
                <View style={styles.insightCard}>
                    <Text style={styles.insightTitle}>Key Insight</Text>
                    <Text style={styles.insightText}>
                        {topCrop.sharePct >= 50
                            ? `${topCrop.crop} makes up ${topCrop.sharePct.toFixed(0)}% of your inventory value. Consider diversifying to reduce risk.`
                            : `Your inventory is well diversified. ${topCrop.crop} leads at ${topCrop.sharePct.toFixed(0)}% of total value.`}
                    </Text>
                </View>
            </ScrollView>
        </SafeAreaView>
    );
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function SummaryCard({
    icon,
    label,
    value,
    highlight = false,
}: {
    icon: React.ReactNode;
    label: string;
    value: string;
    highlight?: boolean;
}) {
    return (
        <View style={[summaryStyles.card, highlight && summaryStyles.cardHighlight]}>
            <View style={summaryStyles.iconRow}>{icon}</View>
            <Text style={summaryStyles.label}>{label}</Text>
            <Text style={[summaryStyles.value, highlight && { color: colors.primary }]}>{value}</Text>
        </View>
    );
}

function CropBreakdownRow({
    rank,
    crop,
    value,
    quantityLabel,
    sharePct,
    color,
}: {
    rank: number;
    crop: string;
    value: number;
    quantityLabel: string;
    sharePct: number;
    color: string;
}) {
    return (
        <View style={breakdownStyles.row}>
            <View style={[breakdownStyles.rankBadge, { backgroundColor: color + '22' }]}>
                <Text style={[breakdownStyles.rankText, { color }]}>#{rank}</Text>
            </View>
            <View style={breakdownStyles.info}>
                <View style={breakdownStyles.topLine}>
                    <Text style={breakdownStyles.cropName}>{crop}</Text>
                    <Text style={breakdownStyles.valueText}>₹{value.toLocaleString('en-IN')}</Text>
                </View>
                <Text style={breakdownStyles.qty}>{quantityLabel}</Text>
                {/* Progress bar */}
                <View style={breakdownStyles.barBg}>
                    <View style={[breakdownStyles.barFill, { width: `${sharePct}%` as any, backgroundColor: color }]} />
                </View>
                <Text style={[breakdownStyles.pct, { color }]}>{sharePct.toFixed(1)}% of total value</Text>
            </View>
        </View>
    );
}

// ─── Constants ───────────────────────────────────────────────────────────────

const CHART_COLORS = [
    colors.primary,
    colors.chart1,
    colors.chart2,
    colors.chart3,
    colors.chart4,
    colors.chart5,
    colors.warning,
    colors.error,
];

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.surface },
    header: {
        padding: spacing[4],
        paddingBottom: spacing[3],
        backgroundColor: colors.background,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
    },
    pageTitle: { fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.foreground },
    pageSubtitle: { fontSize: typography.fontSize.sm, color: colors.muted, marginTop: 2 },
    scroll: { flex: 1 },
    content: { padding: spacing[4], paddingBottom: spacing[8] },
    emptyState: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: spacing[16] },
    emptyTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginTop: spacing[4] },
    emptySubtitle: { fontSize: typography.fontSize.sm, color: colors.muted, marginTop: spacing[2], textAlign: 'center', paddingHorizontal: spacing[8] },
    summaryRow: { flexDirection: 'row', gap: spacing[3], marginBottom: spacing[3] },
    chartCard: {
        backgroundColor: colors.background,
        borderRadius: radii.lg,
        borderWidth: 1,
        borderColor: colors.border,
        padding: spacing[4],
        marginBottom: spacing[4],
        ...shadows.card,
    },
    chartWrapper: { marginTop: spacing[3], alignItems: 'center' },
    chartAxisText: { fontSize: typography.fontSize.xs, color: colors.muted },
    sectionTitle: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginBottom: spacing[1] },
    sectionSubtitle: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: spacing[3] },
    insightCard: {
        backgroundColor: colors.primaryLight,
        borderRadius: radii.lg,
        padding: spacing[4],
        marginTop: spacing[4],
    },
    insightTitle: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, color: colors.primaryDark, marginBottom: spacing[1] },
    insightText: { fontSize: typography.fontSize.sm, color: colors.primaryDark, lineHeight: typography.fontSize.sm * 1.5 },
});

const summaryStyles = StyleSheet.create({
    card: {
        flex: 1,
        backgroundColor: colors.background,
        borderRadius: radii.lg,
        borderWidth: 1,
        borderColor: colors.border,
        padding: spacing[4],
        ...shadows.card,
    },
    cardHighlight: {
        borderColor: colors.primary,
        backgroundColor: colors.primaryLight,
    },
    iconRow: { marginBottom: spacing[2] },
    label: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: spacing[1] },
    value: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.bold, color: colors.foreground },
});

const breakdownStyles = StyleSheet.create({
    row: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        backgroundColor: colors.background,
        borderRadius: radii.lg,
        borderWidth: 1,
        borderColor: colors.border,
        padding: spacing[4],
        marginBottom: spacing[3],
        gap: spacing[3],
        ...shadows.card,
    },
    rankBadge: {
        width: 32,
        height: 32,
        borderRadius: radii.md,
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: 2,
    },
    rankText: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.bold },
    info: { flex: 1 },
    topLine: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 2 },
    cropName: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    valueText: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    qty: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: spacing[2] },
    barBg: {
        height: 6,
        backgroundColor: colors.surface,
        borderRadius: radii.full,
        overflow: 'hidden',
        marginBottom: spacing[1],
    },
    barFill: { height: '100%', borderRadius: radii.full },
    pct: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.medium },
});
