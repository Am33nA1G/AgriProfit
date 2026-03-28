// mobile/src/screens/sales/SalesScreen.tsx
// Record crop sales and view sale history.
// Local state only — no backend dependency required.

import React, { useState } from 'react';
import {
    View,
    Text,
    ScrollView,
    TextInput,
    TouchableOpacity,
    Modal,
    StyleSheet,
    Alert,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Plus, ShoppingCart, IndianRupee } from 'lucide-react-native';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';

interface SaleRecord {
    id: string;
    crop: string;
    quantity: string;
    unit: string;
    pricePerUnit: string;
    buyer: string;
    date: string;
    notes: string;
}

const EMPTY_FORM: Omit<SaleRecord, 'id'> = {
    crop: '',
    quantity: '',
    unit: 'kg',
    pricePerUnit: '',
    buyer: '',
    date: new Date().toISOString().slice(0, 10),
    notes: '',
};

const UNITS = ['kg', 'quintal', 'ton', 'piece'];

function formatDate(iso: string) {
    const [y, m, d] = iso.split('-');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${d} ${months[parseInt(m, 10) - 1]} ${y}`;
}

export function SalesScreen() {
    const [sales, setSales] = useState<SaleRecord[]>([
        { id: '1', crop: 'Tomato', quantity: '50', unit: 'kg', pricePerUnit: '28', buyer: 'Pune Mandi', date: '2026-03-18', notes: '' },
        { id: '2', crop: 'Onion', quantity: '200', unit: 'kg', pricePerUnit: '20', buyer: 'Local Trader', date: '2026-03-15', notes: 'Grade A quality' },
    ]);
    const [modalVisible, setModalVisible] = useState(false);
    const [form, setForm] = useState(EMPTY_FORM);

    function openAdd() {
        setForm({ ...EMPTY_FORM, date: new Date().toISOString().slice(0, 10) });
        setModalVisible(true);
    }

    function recordSale() {
        if (!form.crop.trim()) {
            Alert.alert('Required', 'Please enter a crop name.');
            return;
        }
        if (!form.quantity.trim() || isNaN(Number(form.quantity)) || Number(form.quantity) <= 0) {
            Alert.alert('Invalid', 'Please enter a valid quantity.');
            return;
        }
        if (!form.pricePerUnit.trim() || isNaN(Number(form.pricePerUnit)) || Number(form.pricePerUnit) <= 0) {
            Alert.alert('Invalid', 'Please enter a valid price.');
            return;
        }

        setSales((prev) => [{ id: Date.now().toString(), ...form }, ...prev]);
        setModalVisible(false);
    }

    function deleteSale(id: string) {
        Alert.alert('Delete Sale', 'Remove this sale record?', [
            { text: 'Cancel', style: 'cancel' },
            {
                text: 'Delete',
                style: 'destructive',
                onPress: () => setSales((prev) => prev.filter((s) => s.id !== id)),
            },
        ]);
    }

    const totalRevenue = sales.reduce((sum, s) => {
        return sum + (parseFloat(s.quantity) || 0) * (parseFloat(s.pricePerUnit) || 0);
    }, 0);

    return (
        <SafeAreaView style={styles.safeArea}>
            {/* Header */}
            <View style={styles.header}>
                <View>
                    <Text style={styles.pageTitle}>Sales</Text>
                    <Text style={styles.pageSubtitle}>
                        {sales.length} {sales.length === 1 ? 'record' : 'records'} · Total ₹{totalRevenue.toLocaleString('en-IN')}
                    </Text>
                </View>
                <TouchableOpacity style={styles.addButton} onPress={openAdd}>
                    <Plus size={20} color={colors.background} />
                </TouchableOpacity>
            </View>

            <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
                {sales.length === 0 ? (
                    <View style={styles.emptyState}>
                        <ShoppingCart size={48} color={colors.muted} />
                        <Text style={styles.emptyTitle}>No sales recorded</Text>
                        <Text style={styles.emptySubtitle}>Tap + to record your first sale</Text>
                    </View>
                ) : (
                    sales.map((sale) => (
                        <SaleCard key={sale.id} sale={sale} onDelete={() => deleteSale(sale.id)} />
                    ))
                )}
            </ScrollView>

            {/* Record Sale Modal */}
            <Modal visible={modalVisible} animationType="slide" transparent onRequestClose={() => setModalVisible(false)}>
                <KeyboardAvoidingView
                    style={styles.modalOverlay}
                    behavior={Platform.OS === 'ios' ? 'padding' : undefined}
                >
                    <View style={styles.modalSheet}>
                        <Text style={styles.modalTitle}>Record Sale</Text>

                        <Text style={styles.label}>Crop / Produce *</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="e.g. Tomato, Wheat, Onion"
                            placeholderTextColor={colors.placeholder}
                            value={form.crop}
                            onChangeText={(t) => setForm((f) => ({ ...f, crop: t }))}
                        />

                        <View style={styles.row}>
                            <View style={styles.rowItem}>
                                <Text style={styles.label}>Quantity *</Text>
                                <TextInput
                                    style={styles.input}
                                    placeholder="e.g. 100"
                                    placeholderTextColor={colors.placeholder}
                                    keyboardType="numeric"
                                    value={form.quantity}
                                    onChangeText={(t) => setForm((f) => ({ ...f, quantity: t }))}
                                />
                            </View>
                            <View style={styles.rowItem}>
                                <Text style={styles.label}>Price / unit (₹) *</Text>
                                <TextInput
                                    style={styles.input}
                                    placeholder="e.g. 25"
                                    placeholderTextColor={colors.placeholder}
                                    keyboardType="numeric"
                                    value={form.pricePerUnit}
                                    onChangeText={(t) => setForm((f) => ({ ...f, pricePerUnit: t }))}
                                />
                            </View>
                        </View>

                        <Text style={styles.label}>Unit</Text>
                        <View style={styles.unitRow}>
                            {UNITS.map((u) => (
                                <TouchableOpacity
                                    key={u}
                                    style={[styles.unitChip, form.unit === u && styles.unitChipActive]}
                                    onPress={() => setForm((f) => ({ ...f, unit: u }))}
                                >
                                    <Text style={[styles.unitChipText, form.unit === u && styles.unitChipTextActive]}>
                                        {u}
                                    </Text>
                                </TouchableOpacity>
                            ))}
                        </View>

                        <Text style={styles.label}>Buyer / Mandi</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="e.g. Pune Mandi, Local Trader"
                            placeholderTextColor={colors.placeholder}
                            value={form.buyer}
                            onChangeText={(t) => setForm((f) => ({ ...f, buyer: t }))}
                        />

                        <Text style={styles.label}>Date</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="YYYY-MM-DD"
                            placeholderTextColor={colors.placeholder}
                            value={form.date}
                            onChangeText={(t) => setForm((f) => ({ ...f, date: t }))}
                        />

                        <Text style={styles.label}>Notes (optional)</Text>
                        <TextInput
                            style={[styles.input, styles.inputMultiline]}
                            placeholder="Quality grade, transport details, etc."
                            placeholderTextColor={colors.placeholder}
                            multiline
                            numberOfLines={2}
                            value={form.notes}
                            onChangeText={(t) => setForm((f) => ({ ...f, notes: t }))}
                        />

                        {/* Total preview */}
                        {form.quantity && form.pricePerUnit && !isNaN(Number(form.quantity)) && !isNaN(Number(form.pricePerUnit)) && (
                            <View style={styles.totalPreview}>
                                <IndianRupee size={14} color={colors.primary} />
                                <Text style={styles.totalPreviewText}>
                                    Total: ₹{(Number(form.quantity) * Number(form.pricePerUnit)).toLocaleString('en-IN')}
                                </Text>
                            </View>
                        )}

                        <View style={styles.modalActions}>
                            <TouchableOpacity style={styles.cancelButton} onPress={() => setModalVisible(false)}>
                                <Text style={styles.cancelText}>Cancel</Text>
                            </TouchableOpacity>
                            <TouchableOpacity style={styles.saveButton} onPress={recordSale}>
                                <Text style={styles.saveText}>Record Sale</Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </KeyboardAvoidingView>
            </Modal>
        </SafeAreaView>
    );
}

function SaleCard({ sale, onDelete }: { sale: SaleRecord; onDelete: () => void }) {
    const total = (parseFloat(sale.quantity) || 0) * (parseFloat(sale.pricePerUnit) || 0);
    return (
        <View style={cardStyles.card}>
            <View style={cardStyles.header}>
                <View style={cardStyles.info}>
                    <Text style={cardStyles.crop}>{sale.crop}</Text>
                    <Text style={cardStyles.meta}>
                        {sale.buyer ? `${sale.buyer} · ` : ''}{formatDate(sale.date)}
                    </Text>
                    {sale.notes ? <Text style={cardStyles.notes}>{sale.notes}</Text> : null}
                </View>
                <TouchableOpacity onPress={onDelete} style={cardStyles.deleteBtn}>
                    <Text style={cardStyles.deleteText}>✕</Text>
                </TouchableOpacity>
            </View>
            <View style={cardStyles.stats}>
                <StatPill label="Qty" value={`${sale.quantity} ${sale.unit}`} />
                <StatPill label={`₹ / ${sale.unit}`} value={`₹${sale.pricePerUnit}`} />
                <StatPill label="Total" value={`₹${total.toLocaleString('en-IN')}`} highlight />
            </View>
        </View>
    );
}

function StatPill({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
    return (
        <View style={cardStyles.pill}>
            <Text style={cardStyles.pillLabel}>{label}</Text>
            <Text style={[cardStyles.pillValue, highlight && { color: colors.primary }]}>{value}</Text>
        </View>
    );
}

const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.surface },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: spacing[4],
        paddingBottom: spacing[3],
        backgroundColor: colors.background,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
    },
    pageTitle: { fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.foreground },
    pageSubtitle: { fontSize: typography.fontSize.sm, color: colors.muted, marginTop: 2 },
    addButton: {
        backgroundColor: colors.primary,
        borderRadius: radii.full,
        width: 40,
        height: 40,
        justifyContent: 'center',
        alignItems: 'center',
        ...shadows.card,
    },
    scroll: { flex: 1 },
    content: { padding: spacing[4], paddingBottom: spacing[8] },
    emptyState: { alignItems: 'center', justifyContent: 'center', paddingTop: spacing[16] },
    emptyTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginTop: spacing[4] },
    emptySubtitle: { fontSize: typography.fontSize.sm, color: colors.muted, marginTop: spacing[2] },
    // Modal
    modalOverlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: colors.overlay },
    modalSheet: {
        backgroundColor: colors.background,
        borderTopLeftRadius: radii['2xl'],
        borderTopRightRadius: radii['2xl'],
        padding: spacing[6],
        paddingBottom: spacing[8],
        ...shadows.modal,
    },
    modalTitle: { fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.bold, color: colors.foreground, marginBottom: spacing[2] },
    label: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.foreground, marginBottom: spacing[1], marginTop: spacing[3] },
    input: {
        borderWidth: 1,
        borderColor: colors.inputBorder,
        borderRadius: radii.md,
        padding: spacing[3],
        fontSize: typography.fontSize.base,
        color: colors.foreground,
        backgroundColor: colors.background,
    },
    inputMultiline: { minHeight: 64, textAlignVertical: 'top' },
    row: { flexDirection: 'row', gap: spacing[3] },
    rowItem: { flex: 1 },
    unitRow: { flexDirection: 'row', gap: spacing[2], marginTop: spacing[1] },
    unitChip: {
        borderWidth: 1,
        borderColor: colors.inputBorder,
        borderRadius: radii.full,
        paddingHorizontal: spacing[3],
        paddingVertical: spacing[1],
    },
    unitChipActive: { borderColor: colors.primary, backgroundColor: colors.primaryLight },
    unitChipText: { fontSize: typography.fontSize.sm, color: colors.muted },
    unitChipTextActive: { color: colors.primary, fontWeight: typography.fontWeight.semibold },
    totalPreview: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing[1],
        marginTop: spacing[3],
        backgroundColor: colors.primaryLight,
        padding: spacing[3],
        borderRadius: radii.md,
    },
    totalPreviewText: { fontSize: typography.fontSize.base, color: colors.primary, fontWeight: typography.fontWeight.semibold },
    modalActions: { flexDirection: 'row', gap: spacing[3], marginTop: spacing[6] },
    cancelButton: {
        flex: 1,
        padding: spacing[3],
        borderRadius: radii.md,
        borderWidth: 1,
        borderColor: colors.border,
        alignItems: 'center',
    },
    cancelText: { fontSize: typography.fontSize.base, color: colors.muted, fontWeight: typography.fontWeight.medium },
    saveButton: { flex: 1, padding: spacing[3], borderRadius: radii.md, backgroundColor: colors.primary, alignItems: 'center' },
    saveText: { fontSize: typography.fontSize.base, color: colors.background, fontWeight: typography.fontWeight.semibold },
});

const cardStyles = StyleSheet.create({
    card: {
        backgroundColor: colors.card,
        borderRadius: radii.lg,
        borderWidth: 1,
        borderColor: colors.border,
        padding: spacing[4],
        marginBottom: spacing[3],
        ...shadows.card,
    },
    header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: spacing[3] },
    info: { flex: 1 },
    crop: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    meta: { fontSize: typography.fontSize.sm, color: colors.muted, marginTop: 2 },
    notes: { fontSize: typography.fontSize.xs, color: colors.muted, marginTop: spacing[1] },
    deleteBtn: { padding: spacing[1] },
    deleteText: { fontSize: typography.fontSize.base, color: colors.error },
    stats: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing[2] },
    pill: {
        flex: 1,
        backgroundColor: colors.surface,
        borderRadius: radii.md,
        padding: spacing[2],
        alignItems: 'center',
    },
    pillLabel: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: 2 },
    pillValue: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
});
