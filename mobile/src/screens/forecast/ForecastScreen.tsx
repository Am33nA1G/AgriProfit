// mobile/src/screens/forecast/ForecastScreen.tsx
// 7-day ML price forecast — commodity → state → district cascading selectors,
// direction card, price range, and line chart.

import React, { useState } from 'react';
import {
    View,
    Text,
    ScrollView,
    TextInput,
    TouchableOpacity,
    Modal,
    FlatList,
    StyleSheet,
    ActivityIndicator,
    Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import { LineChart } from 'react-native-gifted-charts';
import {
    BarChart3,
    TrendingUp,
    TrendingDown,
    Minus,
    HelpCircle,
    ChevronDown,
    AlertTriangle,
    Info,
} from 'lucide-react-native';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import { forecastService, type ForecastResponse, type ForecastPoint } from '../../services/forecast';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function slugToLabel(slug: string): string {
    return slug.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatShortDate(iso: string): string {
    const d = new Date(iso);
    return `${d.getDate()}/${d.getMonth() + 1}`;
}

const CONFIDENCE = {
    Green: { label: 'Reliable', color: colors.success, bg: colors.successLight },
    Yellow: { label: 'Directional', color: colors.warning, bg: colors.warningLight },
    Red: { label: 'Low Confidence', color: colors.error, bg: colors.errorLight },
} as const;

const DIRECTION_CONFIG = {
    up: {
        icon: TrendingUp,
        label: 'Price Rising',
        color: colors.success,
        bg: colors.successLight,
    },
    down: {
        icon: TrendingDown,
        label: 'Price Falling',
        color: colors.error,
        bg: colors.errorLight,
    },
    flat: {
        icon: Minus,
        label: 'Stable Price',
        color: colors.muted,
        bg: colors.surface,
    },
    uncertain: {
        icon: HelpCircle,
        label: 'Uncertain',
        color: colors.warning,
        bg: colors.warningLight,
    },
} as const;

const CHART_LINE_COLOR: Record<string, string> = {
    Green: colors.success,
    Yellow: colors.warning,
    Red: colors.error,
};

const CHART_FILL_COLOR: Record<string, string> = {
    Green: colors.successLight,
    Yellow: colors.warningLight,
    Red: colors.errorLight,
};

const SCREEN_WIDTH = Dimensions.get('window').width;

// ─── Screen ───────────────────────────────────────────────────────────────────

export function ForecastScreen() {
    const [commodity, setCommodity] = useState('');
    const [state, setState] = useState('');
    const [district, setDistrict] = useState('');

    const [picker, setPicker] = useState<'commodity' | 'state' | 'district' | null>(null);

    // 1. Commodities
    const { data: commodities = [], isLoading: commoditiesLoading } = useQuery<string[]>({
        queryKey: ['forecast-commodities'],
        queryFn: () => forecastService.getCommodities(),
        staleTime: 60 * 60 * 1000,
    });

    // 2. States for selected commodity
    const { data: states = [], isLoading: statesLoading } = useQuery<string[]>({
        queryKey: ['forecast-states', commodity],
        queryFn: () => forecastService.getStatesForCommodity(commodity),
        enabled: !!commodity,
        staleTime: 60 * 60 * 1000,
    });

    // 3. Districts for selected commodity + state
    const { data: districts = [], isLoading: districtsLoading } = useQuery<string[]>({
        queryKey: ['forecast-districts', commodity, state],
        queryFn: () => forecastService.getDistrictsForCommodityState(commodity, state),
        enabled: !!(commodity && state),
        staleTime: 60 * 60 * 1000,
    });

    // 4. Forecast
    const canFetch = !!(commodity && district);
    const {
        data: forecast,
        isLoading: forecastLoading,
        isError: forecastError,
        error: forecastErrorDetail,
    } = useQuery<ForecastResponse>({
        queryKey: ['forecast', commodity, district],
        queryFn: () => forecastService.getForecast(commodity, district),
        enabled: canFetch,
        staleTime: 5 * 60 * 1000,
        retry: 1,
    });

    function selectCommodity(slug: string) {
        setCommodity(slug);
        setState('');
        setDistrict('');
    }

    function selectState(s: string) {
        setState(s);
        setDistrict('');
    }

    const conf = forecast ? CONFIDENCE[forecast.confidence_colour] : null;
    const dirConf = forecast ? DIRECTION_CONFIG[forecast.direction] : null;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const errorStatus = (forecastErrorDetail as any)?.response?.status;

    return (
        <SafeAreaView style={styles.safeArea}>
            {/* Header */}
            <View style={styles.header}>
                <View style={styles.headerIcon}>
                    <BarChart3 size={20} color={colors.primary} />
                </View>
                <View>
                    <Text style={styles.pageTitle}>Price Forecast</Text>
                    <Text style={styles.pageSubtitle}>7-day ML price predictions</Text>
                </View>
            </View>

            <ScrollView style={styles.scroll} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
                {/* ── Selectors ──────────────────────────────────────────── */}
                <View style={styles.selectorsSection}>
                    <SelectButton
                        label={commoditiesLoading ? 'Loading...' : 'Select Commodity'}
                        value={commodity ? slugToLabel(commodity) : ''}
                        disabled={commoditiesLoading}
                        onPress={() => setPicker('commodity')}
                    />
                    <SelectButton
                        label={!commodity ? 'Select Commodity first' : statesLoading ? 'Loading...' : 'Select State'}
                        value={state}
                        disabled={!commodity || statesLoading}
                        onPress={() => setPicker('state')}
                    />
                    <SelectButton
                        label={!state ? 'Select State first' : districtsLoading ? 'Loading...' : 'Select District'}
                        value={district}
                        disabled={!state || districtsLoading}
                        onPress={() => setPicker('district')}
                    />
                </View>

                {/* ── Empty prompt ───────────────────────────────────────── */}
                {!canFetch && (
                    <View style={styles.emptyState}>
                        <BarChart3 size={48} color={colors.disabled} />
                        <Text style={styles.emptyTitle}>Select a commodity and district</Text>
                        <Text style={styles.emptySubtitle}>
                            Choose a commodity, state, and district to see the 7-day price forecast.
                        </Text>
                    </View>
                )}

                {/* ── Loading ────────────────────────────────────────────── */}
                {canFetch && forecastLoading && (
                    <View style={styles.loadingState}>
                        <ActivityIndicator size="large" color={colors.primary} />
                        <Text style={styles.loadingText}>Generating forecast...</Text>
                    </View>
                )}

                {/* ── Error ──────────────────────────────────────────────── */}
                {canFetch && forecastError && (
                    <View style={styles.errorState}>
                        <AlertTriangle size={36} color={colors.warning} />
                        <Text style={styles.errorText}>
                            {errorStatus === 404
                                ? 'No forecast data available for this combination. Try a different district.'
                                : 'Something went wrong loading the forecast. Please try again.'}
                        </Text>
                    </View>
                )}

                {/* ── Forecast Result ────────────────────────────────────── */}
                {canFetch && forecast && (
                    <View style={styles.resultSection}>
                        {/* Fallback banner */}
                        {forecast.tier_label === 'seasonal average fallback' && (
                            <Banner
                                color="warning"
                                title="Limited Data Coverage"
                                message={forecast.coverage_message ?? 'Insufficient price history. Showing seasonal averages.'}
                            />
                        )}

                        {/* Stale data banner */}
                        {forecast.is_stale && (
                            <Banner
                                color="warning"
                                title={`Data ${forecast.data_freshness_days} day${forecast.data_freshness_days !== 1 ? 's' : ''} old`}
                                message="Live market feed may be unavailable. Forecast is based on the most recent data available."
                            />
                        )}

                        {/* Red confidence warning */}
                        {forecast.confidence_colour === 'Red' && (
                            <Banner
                                color="error"
                                title={`Low Confidence${forecast.mape_pct != null ? ` — ±${forecast.mape_pct.toFixed(0)}% typical error` : ''}`}
                                message="High price volatility or limited market data. Do not use for financial decisions."
                            />
                        )}

                        {/* Direction hero */}
                        {dirConf && (
                            <View style={[styles.directionCard, { backgroundColor: dirConf.bg, borderColor: dirConf.color + '44' }]}>
                                <dirConf.icon size={40} color={dirConf.color} strokeWidth={2} />
                                <View style={styles.directionInfo}>
                                    <Text style={[styles.directionLabel, { color: dirConf.color }]}>
                                        {dirConf.label}
                                    </Text>
                                    <Text style={styles.directionSub}>
                                        {slugToLabel(forecast.commodity)} · {forecast.district} · {forecast.horizon_days} days
                                    </Text>
                                    {conf && (
                                        <View style={[styles.confidenceBadge, { backgroundColor: conf.bg }]}>
                                            <Text style={[styles.confidenceBadgeText, { color: conf.color }]}>
                                                {conf.label}
                                                {forecast.mape_pct != null ? ` · ±${forecast.mape_pct.toFixed(0)}%` : ''}
                                            </Text>
                                        </View>
                                    )}
                                </View>
                            </View>
                        )}

                        {/* Price range */}
                        <PriceRangeCard
                            low={forecast.price_low}
                            mid={forecast.price_mid}
                            high={forecast.price_high}
                        />

                        {/* Chart — hidden for Red confidence */}
                        {forecast.confidence_colour !== 'Red' &&
                            forecast.forecast_points &&
                            forecast.forecast_points.length > 0 && (
                                <ForecastLineChart
                                    points={forecast.forecast_points}
                                    confidenceColour={forecast.confidence_colour}
                                />
                            )}

                        {forecast.confidence_colour === 'Red' && (
                            <Text style={styles.chartHidden}>
                                Chart unavailable for low-confidence forecasts
                            </Text>
                        )}

                        {/* Metadata footer */}
                        <View style={styles.metaFooter}>
                            <Info size={13} color={colors.muted} />
                            <View style={styles.metaTextBlock}>
                                {forecast.n_markets > 0 && (
                                    <Text style={styles.metaText}>
                                        Based on data from {forecast.n_markets} market{forecast.n_markets !== 1 ? 's' : ''}.
                                        {forecast.typical_error_inr != null
                                            ? ` Typical error: ₹${forecast.typical_error_inr}/quintal.`
                                            : ''}
                                    </Text>
                                )}
                                <Text style={styles.metaText}>
                                    Last data: {forecast.last_data_date}. Forecasts are directional signals, not precise predictions.
                                </Text>
                            </View>
                        </View>
                    </View>
                )}
            </ScrollView>

            {/* ── Picker Modals ───────────────────────────────────────────── */}
            <SelectModal
                visible={picker === 'commodity'}
                title="Select Commodity"
                options={commodities}
                formatLabel={slugToLabel}
                onSelect={selectCommodity}
                onClose={() => setPicker(null)}
                searchable
            />
            <SelectModal
                visible={picker === 'state'}
                title="Select State"
                options={states}
                onSelect={selectState}
                onClose={() => setPicker(null)}
            />
            <SelectModal
                visible={picker === 'district'}
                title="Select District"
                options={districts}
                onSelect={(d) => { setDistrict(d); setPicker(null); }}
                onClose={() => setPicker(null)}
                searchable={districts.length > 10}
            />
        </SafeAreaView>
    );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SelectButton({
    label,
    value,
    disabled,
    onPress,
}: {
    label: string;
    value: string;
    disabled?: boolean;
    onPress: () => void;
}) {
    return (
        <TouchableOpacity
            style={[selectBtnStyles.btn, disabled && selectBtnStyles.disabled]}
            onPress={onPress}
            disabled={disabled}
            activeOpacity={0.7}
        >
            <Text
                style={[selectBtnStyles.text, !value && selectBtnStyles.placeholder]}
                numberOfLines={1}
            >
                {value || label}
            </Text>
            <ChevronDown size={16} color={disabled ? colors.disabled : colors.muted} />
        </TouchableOpacity>
    );
}

function SelectModal({
    visible,
    title,
    options,
    formatLabel,
    onSelect,
    onClose,
    searchable = false,
}: {
    visible: boolean;
    title: string;
    options: string[];
    formatLabel?: (v: string) => string;
    onSelect: (value: string) => void;
    onClose: () => void;
    searchable?: boolean;
}) {
    const [search, setSearch] = useState('');
    const fmt = formatLabel ?? ((v: string) => v);
    const filtered = search
        ? options.filter((o) => fmt(o).toLowerCase().includes(search.toLowerCase()))
        : options;

    return (
        <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
            <View style={pickerStyles.overlay}>
                <View style={pickerStyles.sheet}>
                    <View style={pickerStyles.sheetHeader}>
                        <Text style={pickerStyles.sheetTitle}>{title}</Text>
                        <TouchableOpacity onPress={onClose} style={pickerStyles.closeBtn}>
                            <Text style={pickerStyles.closeText}>✕</Text>
                        </TouchableOpacity>
                    </View>

                    {searchable && (
                        <TextInput
                            style={pickerStyles.searchInput}
                            placeholder="Search..."
                            placeholderTextColor={colors.placeholder}
                            value={search}
                            onChangeText={setSearch}
                            autoCorrect={false}
                        />
                    )}

                    <FlatList
                        data={filtered}
                        keyExtractor={(item) => item}
                        style={pickerStyles.list}
                        renderItem={({ item }) => (
                            <TouchableOpacity
                                style={pickerStyles.option}
                                onPress={() => {
                                    setSearch('');
                                    onSelect(item);
                                    onClose();
                                }}
                            >
                                <Text style={pickerStyles.optionText}>{fmt(item)}</Text>
                            </TouchableOpacity>
                        )}
                        ItemSeparatorComponent={() => <View style={pickerStyles.divider} />}
                        keyboardShouldPersistTaps="handled"
                    />
                </View>
            </View>
        </Modal>
    );
}

function Banner({
    color,
    title,
    message,
}: {
    color: 'warning' | 'error';
    title: string;
    message: string;
}) {
    const bg = color === 'error' ? colors.errorLight : colors.warningLight;
    const fg = color === 'error' ? colors.error : colors.warning;
    return (
        <View style={[bannerStyles.banner, { backgroundColor: bg, borderColor: fg + '55' }]}>
            <AlertTriangle size={16} color={fg} style={bannerStyles.icon} />
            <View style={bannerStyles.body}>
                <Text style={[bannerStyles.title, { color: fg }]}>{title}</Text>
                <Text style={[bannerStyles.msg, { color: fg }]}>{message}</Text>
            </View>
        </View>
    );
}

function PriceRangeCard({
    low,
    mid,
    high,
}: {
    low: number | null;
    mid: number | null;
    high: number | null;
}) {
    const fmt = (v: number | null) =>
        v != null ? `₹${Math.round(v).toLocaleString('en-IN')}` : '—';

    return (
        <View style={priceStyles.card}>
            <Text style={priceStyles.title}>Expected Price Range</Text>
            <Text style={priceStyles.subtitle}>Per quintal over next 7 days</Text>
            <View style={priceStyles.row}>
                <PriceCol label="Low" value={fmt(low)} color={colors.error} />
                <PriceCol label="Mid" value={fmt(mid)} color={colors.primary} highlight />
                <PriceCol label="High" value={fmt(high)} color={colors.success} />
            </View>
        </View>
    );
}

function PriceCol({
    label,
    value,
    color,
    highlight = false,
}: {
    label: string;
    value: string;
    color: string;
    highlight?: boolean;
}) {
    return (
        <View style={[priceStyles.col, highlight && { borderWidth: 1, borderColor: color + '55', borderRadius: radii.md }]}>
            <Text style={priceStyles.colLabel}>{label}</Text>
            <Text style={[priceStyles.colValue, { color }]}>{value}</Text>
        </View>
    );
}

function ForecastLineChart({
    points,
    confidenceColour,
}: {
    points: ForecastPoint[];
    confidenceColour: 'Green' | 'Yellow' | 'Red';
}) {
    const lineColor = CHART_LINE_COLOR[confidenceColour];
    const fillColor = CHART_FILL_COLOR[confidenceColour];

    const validPoints = points.filter((p) => p.price_mid != null);
    if (validPoints.length === 0) return null;

    const chartData = validPoints.map((p) => ({
        value: Math.round(p.price_mid!),
        label: formatShortDate(p.date),
    }));

    const chartWidth = SCREEN_WIDTH - spacing[4] * 2 - spacing[4] * 2 - 8; // screen - outer padding - card padding

    return (
        <View style={chartStyles.card}>
            <Text style={chartStyles.title}>7-Day Price Forecast</Text>
            <Text style={chartStyles.subtitle}>Predicted modal price (₹/quintal)</Text>
            <View style={chartStyles.chartArea}>
                <LineChart
                    data={chartData}
                    color={lineColor}
                    thickness={2.5}
                    areaChart
                    startFillColor={fillColor}
                    endFillColor="transparent"
                    startOpacity={0.5}
                    endOpacity={0.05}
                    height={160}
                    width={chartWidth}
                    dataPointsColor={lineColor}
                    dataPointsRadius={4}
                    yAxisTextStyle={chartStyles.axisText}
                    xAxisLabelTextStyle={chartStyles.axisText}
                    yAxisThickness={0}
                    xAxisThickness={1}
                    xAxisColor={colors.border}
                    hideRules={false}
                    rulesColor={colors.border}
                    noOfSections={4}
                    isAnimated
                    curved
                />
            </View>
        </View>
    );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.surface },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing[3],
        padding: spacing[4],
        paddingBottom: spacing[3],
        backgroundColor: colors.background,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
    },
    headerIcon: {
        width: 36,
        height: 36,
        borderRadius: radii.lg,
        backgroundColor: colors.primaryLight,
        justifyContent: 'center',
        alignItems: 'center',
    },
    pageTitle: { fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.foreground },
    pageSubtitle: { fontSize: typography.fontSize.sm, color: colors.muted },
    scroll: { flex: 1 },
    content: { padding: spacing[4], paddingBottom: spacing[8] },
    selectorsSection: { gap: spacing[2], marginBottom: spacing[4] },
    emptyState: { alignItems: 'center', paddingTop: spacing[12], paddingHorizontal: spacing[8] },
    emptyTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginTop: spacing[4], textAlign: 'center' },
    emptySubtitle: { fontSize: typography.fontSize.sm, color: colors.muted, marginTop: spacing[2], textAlign: 'center', lineHeight: typography.fontSize.sm * 1.5 },
    loadingState: { alignItems: 'center', paddingTop: spacing[12], gap: spacing[3] },
    loadingText: { fontSize: typography.fontSize.sm, color: colors.muted },
    errorState: { alignItems: 'center', paddingTop: spacing[12], paddingHorizontal: spacing[8], gap: spacing[3] },
    errorText: { fontSize: typography.fontSize.sm, color: colors.muted, textAlign: 'center', lineHeight: typography.fontSize.sm * 1.5 },
    resultSection: { gap: spacing[3] },
    directionCard: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing[4],
        padding: spacing[5],
        borderRadius: radii.xl,
        borderWidth: 1,
        ...shadows.card,
    },
    directionInfo: { flex: 1 },
    directionLabel: { fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, marginBottom: spacing[1] },
    directionSub: { fontSize: typography.fontSize.sm, color: colors.muted, marginBottom: spacing[2] },
    confidenceBadge: {
        alignSelf: 'flex-start',
        paddingHorizontal: spacing[3],
        paddingVertical: spacing[1],
        borderRadius: radii.full,
    },
    confidenceBadgeText: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold },
    chartHidden: { fontSize: typography.fontSize.xs, color: colors.muted, textAlign: 'center', paddingVertical: spacing[4] },
    metaFooter: {
        flexDirection: 'row',
        gap: spacing[2],
        alignItems: 'flex-start',
        paddingTop: spacing[2],
    },
    metaTextBlock: { flex: 1 },
    metaText: { fontSize: typography.fontSize.xs, color: colors.muted, lineHeight: typography.fontSize.xs * 1.6 },
});

const selectBtnStyles = StyleSheet.create({
    btn: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderWidth: 1,
        borderColor: colors.inputBorder,
        borderRadius: radii.md,
        paddingHorizontal: spacing[3],
        paddingVertical: spacing[3],
        backgroundColor: colors.background,
    },
    disabled: { backgroundColor: colors.surface, borderColor: colors.border },
    text: { fontSize: typography.fontSize.base, color: colors.foreground, flex: 1 },
    placeholder: { color: colors.placeholder },
});

const pickerStyles = StyleSheet.create({
    overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: colors.overlay },
    sheet: {
        backgroundColor: colors.background,
        borderTopLeftRadius: radii['2xl'],
        borderTopRightRadius: radii['2xl'],
        paddingTop: spacing[4],
        maxHeight: '75%',
        ...shadows.modal,
    },
    sheetHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: spacing[5],
        paddingBottom: spacing[3],
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
    },
    sheetTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    closeBtn: { padding: spacing[1] },
    closeText: { fontSize: typography.fontSize.lg, color: colors.muted },
    searchInput: {
        margin: spacing[4],
        marginBottom: spacing[2],
        borderWidth: 1,
        borderColor: colors.inputBorder,
        borderRadius: radii.md,
        paddingHorizontal: spacing[3],
        paddingVertical: spacing[2],
        fontSize: typography.fontSize.base,
        color: colors.foreground,
        backgroundColor: colors.background,
    },
    list: { paddingHorizontal: spacing[2] },
    option: { paddingHorizontal: spacing[3], paddingVertical: spacing[4] },
    optionText: { fontSize: typography.fontSize.base, color: colors.foreground },
    divider: { height: 1, backgroundColor: colors.border, marginHorizontal: spacing[3] },
});

const bannerStyles = StyleSheet.create({
    banner: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: spacing[3],
        padding: spacing[4],
        borderRadius: radii.lg,
        borderWidth: 1,
    },
    icon: { marginTop: 1 },
    body: { flex: 1 },
    title: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, marginBottom: spacing[1] },
    msg: { fontSize: typography.fontSize.sm, lineHeight: typography.fontSize.sm * 1.5 },
});

const priceStyles = StyleSheet.create({
    card: {
        backgroundColor: colors.background,
        borderRadius: radii.lg,
        borderWidth: 1,
        borderColor: colors.border,
        padding: spacing[4],
        ...shadows.card,
    },
    title: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginBottom: 2 },
    subtitle: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: spacing[4] },
    row: { flexDirection: 'row', justifyContent: 'space-around' },
    col: { alignItems: 'center', flex: 1, paddingVertical: spacing[2] },
    colLabel: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: spacing[1] },
    colValue: { fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.bold },
});

const chartStyles = StyleSheet.create({
    card: {
        backgroundColor: colors.background,
        borderRadius: radii.lg,
        borderWidth: 1,
        borderColor: colors.border,
        padding: spacing[4],
        ...shadows.card,
    },
    title: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginBottom: 2 },
    subtitle: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: spacing[3] },
    chartArea: { alignItems: 'center', overflow: 'hidden' },
    axisText: { fontSize: 10, color: colors.muted },
});
