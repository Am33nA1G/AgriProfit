// mobile/src/screens/transport/TransportScreen.tsx
// Find best mandis to sell a commodity — form + ranked results.

import React, { useState } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    FlatList,
    ScrollView,
    Modal,
    StyleSheet,
    ActivityIndicator,
    Alert,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Truck, ChevronDown, ChevronUp, Search, Edit2 } from 'lucide-react-native';
import { useQuery } from '@tanstack/react-query';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import { transportService, type MandiComparison } from '../../services/transport';
import { STATE_DISTRICTS, STATES } from '../../data/stateDistricts';
import api from '../../lib/api';

// ─── Constants ────────────────────────────────────────────────────────────────

const VERDICT_COLORS: Record<MandiComparison['verdict'], string> = {
    excellent: '#16a34a',
    good: '#2563eb',
    marginal: '#d97706',
    not_viable: '#dc2626',
};

const VERDICT_BG: Record<MandiComparison['verdict'], string> = {
    excellent: '#dcfce7',
    good: '#dbeafe',
    marginal: '#fef3c7',
    not_viable: '#fee2e2',
};

const VERDICT_LABELS: Record<MandiComparison['verdict'], string> = {
    excellent: 'Excellent',
    good: 'Good',
    marginal: 'Marginal',
    not_viable: 'Not Viable',
};

// ─── CostRow ──────────────────────────────────────────────────────────────────

function CostRow({ label, value }: { label: string; value: number }) {
    if (value === 0) return null;
    return (
        <View style={styles.costRow}>
            <Text style={styles.costLabel}>{label}</Text>
            <Text style={styles.costValue}>₹{value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</Text>
        </View>
    );
}

// ─── MandiCard ────────────────────────────────────────────────────────────────

function MandiCard({ item }: { item: MandiComparison }) {
    const [expanded, setExpanded] = useState(false);
    const profitColor = item.net_profit >= 0 ? colors.success : colors.error;

    return (
        <TouchableOpacity style={styles.card} onPress={() => setExpanded(e => !e)} activeOpacity={0.85}>
            <View style={styles.cardTop}>
                <View style={styles.cardLeft}>
                    <Text style={styles.mandiName}>{item.mandi_name}</Text>
                    <Text style={styles.mandiMeta}>{item.district}, {item.state}</Text>
                    <Text style={styles.mandiMeta}>
                        {item.distance_km.toFixed(0)} km · {item.travel_time_hours.toFixed(1)}h
                    </Text>
                </View>
                <View style={styles.cardRight}>
                    <View style={[styles.verdictBadge, { backgroundColor: VERDICT_BG[item.verdict] }]}>
                        <Text style={[styles.verdictText, { color: VERDICT_COLORS[item.verdict] }]}>
                            {VERDICT_LABELS[item.verdict]}
                        </Text>
                    </View>
                    <Text style={[styles.profitAmount, { color: profitColor }]}>
                        ₹{Math.abs(item.net_profit).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        {item.net_profit < 0 ? ' loss' : ''}
                    </Text>
                    <Text style={styles.roiText}>ROI {item.roi_percentage.toFixed(1)}%</Text>
                </View>
            </View>

            <View style={styles.expandHint}>
                {expanded ? <ChevronUp size={14} color={colors.muted} /> : <ChevronDown size={14} color={colors.muted} />}
                <Text style={styles.expandHintText}>{expanded ? 'Hide costs' : 'Show costs'}</Text>
            </View>

            {expanded && (
                <View style={styles.costBreakdown}>
                    <CostRow label="Freight" value={item.costs.transport_cost} />
                    <CostRow label="Loading hamali" value={item.costs.loading_hamali} />
                    <CostRow label="Unloading hamali" value={item.costs.unloading_hamali} />
                    <CostRow label="Toll" value={item.costs.toll_cost} />
                    <CostRow label="Mandi fee" value={item.costs.mandi_fee} />
                    <CostRow label="Commission" value={item.costs.commission} />
                    <CostRow label="Driver bata" value={item.costs.driver_bata} />
                    <CostRow label="Permit" value={item.costs.permit_cost} />
                    <View style={[styles.costRow, styles.costRowTotal]}>
                        <Text style={styles.costLabelBold}>Total costs</Text>
                        <Text style={styles.costValueBold}>₹{item.costs.total_cost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</Text>
                    </View>
                    {item.economic_warning ? (
                        <Text style={styles.warning}>⚠ {item.economic_warning}</Text>
                    ) : null}
                </View>
            )}
        </TouchableOpacity>
    );
}

// ─── PickerModal ──────────────────────────────────────────────────────────────

function PickerModal({
    visible, title, options, selected, onSelect, onClose,
}: {
    visible: boolean; title: string; options: string[];
    selected: string; onSelect: (v: string) => void; onClose: () => void;
}) {
    return (
        <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
            <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={onClose} />
            <View style={styles.pickerSheet}>
                <Text style={styles.pickerTitle}>{title}</Text>
                <FlatList
                    data={options}
                    keyExtractor={item => item}
                    renderItem={({ item }) => (
                        <TouchableOpacity
                            style={[styles.pickerItem, item === selected && styles.pickerItemSelected]}
                            onPress={() => { onSelect(item); onClose(); }}
                        >
                            <Text style={[styles.pickerItemText, item === selected && styles.pickerItemTextSelected]}>
                                {item}
                            </Text>
                        </TouchableOpacity>
                    )}
                />
            </View>
        </Modal>
    );
}

// ─── Screen ───────────────────────────────────────────────────────────────────

export function TransportScreen() {
    const [commodity, setCommodity] = useState('');
    const [commoditySearch, setCommoditySearch] = useState('');
    const [showCommodityDropdown, setShowCommodityDropdown] = useState(false);
    const [quantity, setQuantity] = useState('');
    const [unit, setUnit] = useState<'kg' | 'quintal'>('kg');
    const [sourceState, setSourceState] = useState('Kerala');
    const [sourceDistrict, setSourceDistrict] = useState('');
    const [showStatePicker, setShowStatePicker] = useState(false);
    const [showDistrictPicker, setShowDistrictPicker] = useState(false);
    const [results, setResults] = useState<MandiComparison[] | null>(null);
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState<Record<string, string>>({});

    const districts = STATE_DISTRICTS[sourceState] ?? [];

    const { data: commoditySuggestions } = useQuery({
        queryKey: ['commodity-search', commoditySearch],
        queryFn: async () => {
            if (commoditySearch.length < 2) return [];
            const { data } = await api.get('/commodities/search/', { params: { q: commoditySearch, limit: 20 } });
            return data as { id: string; name: string }[];
        },
        enabled: commoditySearch.length >= 2,
        staleTime: 60000,
    });

    function validate(): boolean {
        const e: Record<string, string> = {};
        if (!commodity) e.commodity = 'Select a commodity';
        if (!quantity || isNaN(Number(quantity)) || Number(quantity) <= 0) {
            e.quantity = 'Enter a valid quantity';
        } else {
            const qty_kg = Number(quantity) * (unit === 'quintal' ? 100 : 1);
            if (qty_kg > 50000) e.quantity = 'Maximum 50,000 kg (500 quintals)';
        }
        if (!sourceDistrict) e.district = 'Select a district';
        setErrors(e);
        return Object.keys(e).length === 0;
    }

    async function handleSearch() {
        if (!validate()) return;
        setLoading(true);
        try {
            const qty_kg = Number(quantity) * (unit === 'quintal' ? 100 : 1);
            const data = await transportService.compare({
                commodity,
                quantity_kg: qty_kg,
                source_state: sourceState,
                source_district: sourceDistrict,
            });
            setResults(data);
        } catch (err: unknown) {
            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            Alert.alert('Error', msg ?? 'Could not reach server. Check your connection.');
        } finally {
            setLoading(false);
        }
    }

    // ── Form View ─────────────────────────────────────────────────────────────
    if (results === null) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.header}>
                    <Truck size={20} color={colors.primary} />
                    <Text style={styles.headerTitle}>Find Best Mandi</Text>
                </View>

                <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
                    <ScrollView style={styles.scroll} contentContainerStyle={styles.formContent} keyboardShouldPersistTaps="handled">

                        {/* Commodity */}
                        <Text style={styles.label}>Commodity</Text>
                        <View>
                            <View style={styles.inputRow}>
                                <Search size={16} color={colors.muted} style={{ marginLeft: spacing[3] }} />
                                <TextInput
                                    style={styles.inputWithIcon}
                                    placeholder="Search commodity…"
                                    value={commoditySearch}
                                    onChangeText={v => {
                                        setCommoditySearch(v);
                                        if (v !== commodity) setCommodity('');
                                        setShowCommodityDropdown(true);
                                    }}
                                    onFocus={() => setShowCommodityDropdown(true)}
                                    placeholderTextColor={colors.muted}
                                />
                            </View>
                            {errors.commodity ? <Text style={styles.errorText}>{errors.commodity}</Text> : null}
                            {showCommodityDropdown && (commoditySuggestions?.length ?? 0) > 0 && (
                                <View style={styles.dropdown}>
                                    {(commoditySuggestions ?? []).map(c => (
                                        <TouchableOpacity
                                            key={c.id}
                                            style={styles.dropdownItem}
                                            onPress={() => {
                                                setCommodity(c.name);
                                                setCommoditySearch(c.name);
                                                setShowCommodityDropdown(false);
                                            }}
                                        >
                                            <Text style={styles.dropdownItemText}>{c.name}</Text>
                                        </TouchableOpacity>
                                    ))}
                                </View>
                            )}
                        </View>

                        {/* Quantity */}
                        <Text style={styles.label}>Quantity</Text>
                        <View style={styles.quantityRow}>
                            <TextInput
                                style={[styles.input, styles.quantityInput]}
                                placeholder="0"
                                value={quantity}
                                onChangeText={setQuantity}
                                keyboardType="numeric"
                                placeholderTextColor={colors.muted}
                            />
                            <TouchableOpacity
                                style={[styles.unitToggle, unit === 'kg' && styles.unitToggleActive]}
                                onPress={() => setUnit('kg')}
                            >
                                <Text style={[styles.unitToggleText, unit === 'kg' && styles.unitToggleTextActive]}>kg</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[styles.unitToggle, unit === 'quintal' && styles.unitToggleActive]}
                                onPress={() => setUnit('quintal')}
                            >
                                <Text style={[styles.unitToggleText, unit === 'quintal' && styles.unitToggleTextActive]}>qtl</Text>
                            </TouchableOpacity>
                        </View>
                        {errors.quantity ? <Text style={styles.errorText}>{errors.quantity}</Text> : null}

                        {/* Source State */}
                        <Text style={styles.label}>Source State</Text>
                        <TouchableOpacity style={styles.picker} onPress={() => setShowStatePicker(true)}>
                            <Text style={styles.pickerValue}>{sourceState}</Text>
                            <ChevronDown size={16} color={colors.muted} />
                        </TouchableOpacity>

                        {/* Source District */}
                        <Text style={styles.label}>Source District</Text>
                        <TouchableOpacity
                            style={[styles.picker, !sourceState && styles.pickerDisabled]}
                            onPress={() => sourceState ? setShowDistrictPicker(true) : undefined}
                            disabled={!sourceState}
                        >
                            <Text style={[styles.pickerValue, !sourceDistrict && { color: colors.muted }]}>
                                {sourceDistrict || 'Select district…'}
                            </Text>
                            <ChevronDown size={16} color={colors.muted} />
                        </TouchableOpacity>
                        {errors.district ? <Text style={styles.errorText}>{errors.district}</Text> : null}

                        <TouchableOpacity
                            style={[styles.searchBtn, loading && styles.searchBtnDisabled]}
                            onPress={handleSearch}
                            disabled={loading}
                        >
                            {loading
                                ? <ActivityIndicator color="#fff" size="small" />
                                : <Text style={styles.searchBtnText}>Find Best Mandis</Text>
                            }
                        </TouchableOpacity>
                    </ScrollView>
                </KeyboardAvoidingView>

                <PickerModal
                    visible={showStatePicker} title="Select State" options={STATES} selected={sourceState}
                    onSelect={v => { setSourceState(v); setSourceDistrict(''); }}
                    onClose={() => setShowStatePicker(false)}
                />
                <PickerModal
                    visible={showDistrictPicker} title="Select District" options={districts} selected={sourceDistrict}
                    onSelect={setSourceDistrict} onClose={() => setShowDistrictPicker(false)}
                />
            </SafeAreaView>
        );
    }

    // ── Results View ──────────────────────────────────────────────────────────
    return (
        <SafeAreaView style={styles.safeArea}>
            <View style={styles.resultsHeader}>
                <Text style={styles.resultsTitle} numberOfLines={1}>{commodity} · {quantity} {unit}</Text>
                <TouchableOpacity style={styles.editBtn} onPress={() => setResults(null)}>
                    <Edit2 size={14} color={colors.primary} />
                    <Text style={styles.editBtnText}>Edit</Text>
                </TouchableOpacity>
            </View>

            {results.length === 0 ? (
                <View style={styles.emptyState}>
                    <Text style={styles.emptyText}>No mandis found for this search.</Text>
                </View>
            ) : (
                <FlatList
                    data={results}
                    keyExtractor={item => `${item.mandi_name}-${item.district}`}
                    renderItem={({ item }) => <MandiCard item={item} />}
                    contentContainerStyle={styles.listContent}
                />
            )}
        </SafeAreaView>
    );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.background },
    header: { flexDirection: 'row', alignItems: 'center', gap: spacing[2], paddingHorizontal: spacing[4], paddingTop: spacing[4], paddingBottom: spacing[3] },
    headerTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground },
    scroll: { flex: 1 },
    formContent: { padding: spacing[4], gap: spacing[3] },
    label: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.foreground, marginBottom: 2 },
    input: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground, backgroundColor: colors.card },
    inputRow: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, backgroundColor: colors.card },
    inputWithIcon: { flex: 1, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground },
    quantityRow: { flexDirection: 'row', gap: spacing[2] },
    quantityInput: { flex: 1 },
    unitToggle: { paddingHorizontal: spacing[3], paddingVertical: spacing[2], borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, backgroundColor: colors.card },
    unitToggleActive: { backgroundColor: colors.primary, borderColor: colors.primary },
    unitToggleText: { fontSize: typography.fontSize.sm, color: colors.muted },
    unitToggleTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
    picker: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], backgroundColor: colors.card },
    pickerDisabled: { opacity: 0.5 },
    pickerValue: { fontSize: typography.fontSize.base, color: colors.foreground },
    dropdown: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, backgroundColor: colors.card, maxHeight: 180, ...shadows.card },
    dropdownItem: { paddingHorizontal: spacing[3], paddingVertical: spacing[2] },
    dropdownItemText: { fontSize: typography.fontSize.base, color: colors.foreground },
    searchBtn: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: spacing[3], alignItems: 'center', marginTop: spacing[2] },
    searchBtnDisabled: { opacity: 0.6 },
    searchBtnText: { color: '#fff', fontWeight: typography.fontWeight.semibold, fontSize: typography.fontSize.base },
    errorText: { fontSize: typography.fontSize.xs, color: colors.error, marginTop: 2 },
    resultsHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing[4], paddingVertical: spacing[3], borderBottomWidth: 1, borderBottomColor: colors.border },
    resultsTitle: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground, flex: 1 },
    editBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
    editBtnText: { fontSize: typography.fontSize.sm, color: colors.primary },
    listContent: { padding: spacing[4], gap: spacing[3] },
    emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center' },
    emptyText: { color: colors.muted, fontSize: typography.fontSize.base },
    card: { backgroundColor: colors.card, borderRadius: radii.lg, padding: spacing[3], borderWidth: 1, borderColor: colors.border, ...shadows.sm },
    cardTop: { flexDirection: 'row', justifyContent: 'space-between' },
    cardLeft: { flex: 1 },
    cardRight: { alignItems: 'flex-end', gap: 4 },
    mandiName: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    mandiMeta: { fontSize: typography.fontSize.xs, color: colors.muted, marginTop: 2 },
    verdictBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: radii.sm },
    verdictText: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold },
    profitAmount: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold },
    roiText: { fontSize: typography.fontSize.xs, color: colors.muted },
    expandHint: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, marginTop: spacing[2], paddingTop: spacing[2], borderTopWidth: 1, borderTopColor: colors.border },
    expandHintText: { fontSize: typography.fontSize.xs, color: colors.muted },
    costBreakdown: { marginTop: spacing[2], gap: 4 },
    costRow: { flexDirection: 'row', justifyContent: 'space-between' },
    costRowTotal: { borderTopWidth: 1, borderTopColor: colors.border, marginTop: 4, paddingTop: 4 },
    costLabel: { fontSize: typography.fontSize.xs, color: colors.muted },
    costValue: { fontSize: typography.fontSize.xs, color: colors.foreground },
    costLabelBold: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    costValueBold: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    warning: { fontSize: typography.fontSize.xs, color: colors.warning, marginTop: 4 },
    modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
    pickerSheet: { backgroundColor: colors.background, borderTopLeftRadius: radii.xl, borderTopRightRadius: radii.xl, maxHeight: '60%', paddingBottom: spacing[8] },
    pickerTitle: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, padding: spacing[4], borderBottomWidth: 1, borderBottomColor: colors.border },
    pickerItem: { paddingHorizontal: spacing[4], paddingVertical: spacing[3] },
    pickerItemSelected: { backgroundColor: colors.primaryLight },
    pickerItemText: { fontSize: typography.fontSize.base, color: colors.foreground },
    pickerItemTextSelected: { color: colors.primary, fontWeight: typography.fontWeight.medium },
});
