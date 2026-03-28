// mobile/src/screens/inventory/InventoryScreen.tsx
// View and update the farmer's crop inventory.
// State managed in inventoryStore (shared with InventoryAnalysisScreen).

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
import { Plus, Pencil, Trash2, Package } from 'lucide-react-native';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import { useInventoryStore, type InventoryItem } from '../../store/inventoryStore';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { InventoryStackParamList } from '../../navigation/InventoryStack';

type Props = {
    navigation: NativeStackNavigationProp<InventoryStackParamList, 'Inventory'>;
};

const EMPTY_FORM: Omit<InventoryItem, 'id'> = {
    crop: '',
    quantity: '',
    unit: 'kg',
    pricePerUnit: '',
    notes: '',
};

const UNITS = ['kg', 'quintal', 'ton', 'piece'];

export function InventoryScreen({ navigation }: Props) {
    const { items, addItem, updateItem, deleteItem: storeDeleteItem } = useInventoryStore();
    const [modalVisible, setModalVisible] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState(EMPTY_FORM);

    function openAdd() {
        setEditingId(null);
        setForm(EMPTY_FORM);
        setModalVisible(true);
    }

    function openEdit(item: InventoryItem) {
        setEditingId(item.id);
        setForm({ crop: item.crop, quantity: item.quantity, unit: item.unit, pricePerUnit: item.pricePerUnit, notes: item.notes });
        setModalVisible(true);
    }

    function saveItem() {
        if (!form.crop.trim()) {
            Alert.alert('Required', 'Please enter a crop name.');
            return;
        }
        if (!form.quantity.trim() || isNaN(Number(form.quantity))) {
            Alert.alert('Invalid', 'Please enter a valid quantity.');
            return;
        }

        if (editingId) {
            updateItem(editingId, form);
        } else {
            addItem(form);
        }
        setModalVisible(false);
    }

    function deleteItem(id: string) {
        Alert.alert('Delete Item', 'Remove this item from inventory?', [
            { text: 'Cancel', style: 'cancel' },
            {
                text: 'Delete',
                style: 'destructive',
                onPress: () => storeDeleteItem(id),
            },
        ]);
    }

    const totalValue = items.reduce((sum, it) => {
        const qty = parseFloat(it.quantity) || 0;
        const price = parseFloat(it.pricePerUnit) || 0;
        return sum + qty * price;
    }, 0);

    return (
        <SafeAreaView style={styles.safeArea}>
            {/* Header */}
            <View style={styles.header}>
                <View>
                    <Text style={styles.pageTitle}>Inventory</Text>
                    <Text style={styles.pageSubtitle}>
                        {items.length} {items.length === 1 ? 'item' : 'items'} · Est. value ₹{totalValue.toLocaleString('en-IN')}
                    </Text>
                </View>
                <View style={styles.headerActions}>
                    <TouchableOpacity style={styles.analyzeBtn} onPress={() => navigation.navigate('InventoryAnalysis')}>
                        <Text style={styles.analyzeBtnText}>Analyze →</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.addButton} onPress={openAdd}>
                        <Plus size={20} color={colors.background} />
                    </TouchableOpacity>
                </View>
            </View>

            <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
                {items.length === 0 ? (
                    <View style={styles.emptyState}>
                        <Package size={48} color={colors.muted} />
                        <Text style={styles.emptyTitle}>No inventory yet</Text>
                        <Text style={styles.emptySubtitle}>Tap + to add your first item</Text>
                    </View>
                ) : (
                    items.map((item) => (
                        <InventoryCard
                            key={item.id}
                            item={item}
                            onEdit={() => openEdit(item)}
                            onDelete={() => deleteItem(item.id)}
                        />
                    ))
                )}
            </ScrollView>

            {/* Add / Edit Modal */}
            <Modal visible={modalVisible} animationType="slide" transparent onRequestClose={() => setModalVisible(false)}>
                <KeyboardAvoidingView
                    style={styles.modalOverlay}
                    behavior={Platform.OS === 'ios' ? 'padding' : undefined}
                >
                    <View style={styles.modalSheet}>
                        <Text style={styles.modalTitle}>{editingId ? 'Edit Item' : 'Add Item'}</Text>

                        <Text style={styles.label}>Crop / Produce *</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="e.g. Tomato, Wheat, Onion"
                            placeholderTextColor={colors.placeholder}
                            value={form.crop}
                            onChangeText={(t) => setForm((f) => ({ ...f, crop: t }))}
                        />

                        <Text style={styles.label}>Quantity *</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="e.g. 100"
                            placeholderTextColor={colors.placeholder}
                            keyboardType="numeric"
                            value={form.quantity}
                            onChangeText={(t) => setForm((f) => ({ ...f, quantity: t }))}
                        />

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

                        <Text style={styles.label}>Price per {form.unit} (₹)</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="e.g. 25"
                            placeholderTextColor={colors.placeholder}
                            keyboardType="numeric"
                            value={form.pricePerUnit}
                            onChangeText={(t) => setForm((f) => ({ ...f, pricePerUnit: t }))}
                        />

                        <Text style={styles.label}>Notes (optional)</Text>
                        <TextInput
                            style={[styles.input, styles.inputMultiline]}
                            placeholder="Storage location, quality, etc."
                            placeholderTextColor={colors.placeholder}
                            multiline
                            numberOfLines={2}
                            value={form.notes}
                            onChangeText={(t) => setForm((f) => ({ ...f, notes: t }))}
                        />

                        <View style={styles.modalActions}>
                            <TouchableOpacity style={styles.cancelButton} onPress={() => setModalVisible(false)}>
                                <Text style={styles.cancelText}>Cancel</Text>
                            </TouchableOpacity>
                            <TouchableOpacity style={styles.saveButton} onPress={saveItem}>
                                <Text style={styles.saveText}>{editingId ? 'Update' : 'Add'}</Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </KeyboardAvoidingView>
            </Modal>
        </SafeAreaView>
    );
}

function InventoryCard({
    item,
    onEdit,
    onDelete,
}: {
    item: InventoryItem;
    onEdit: () => void;
    onDelete: () => void;
}) {
    const value = (parseFloat(item.quantity) || 0) * (parseFloat(item.pricePerUnit) || 0);
    return (
        <View style={cardStyles.card}>
            <View style={cardStyles.top}>
                <View style={cardStyles.info}>
                    <Text style={cardStyles.crop}>{item.crop}</Text>
                    {item.notes ? <Text style={cardStyles.notes}>{item.notes}</Text> : null}
                </View>
                <View style={cardStyles.actions}>
                    <TouchableOpacity onPress={onEdit} style={cardStyles.actionBtn}>
                        <Pencil size={16} color={colors.primary} />
                    </TouchableOpacity>
                    <TouchableOpacity onPress={onDelete} style={cardStyles.actionBtn}>
                        <Trash2 size={16} color={colors.error} />
                    </TouchableOpacity>
                </View>
            </View>
            <View style={cardStyles.bottom}>
                <Stat label="Quantity" value={`${item.quantity} ${item.unit}`} />
                <Stat label={`Price / ${item.unit}`} value={`₹${item.pricePerUnit}`} />
                <Stat label="Est. Value" value={`₹${value.toLocaleString('en-IN')}`} highlight />
            </View>
        </View>
    );
}

function Stat({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
    return (
        <View style={cardStyles.stat}>
            <Text style={cardStyles.statLabel}>{label}</Text>
            <Text style={[cardStyles.statValue, highlight && { color: colors.primary }]}>{value}</Text>
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
    modalTitle: { fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.bold, color: colors.foreground, marginBottom: spacing[4] },
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
    headerActions: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
    analyzeBtn: { paddingHorizontal: spacing[3], paddingVertical: spacing[1] },
    analyzeBtnText: { fontSize: typography.fontSize.sm, color: colors.primary, fontWeight: typography.fontWeight.medium },
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
    top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: spacing[3] },
    info: { flex: 1 },
    crop: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    notes: { fontSize: typography.fontSize.sm, color: colors.muted, marginTop: 2 },
    actions: { flexDirection: 'row', gap: spacing[2] },
    actionBtn: { padding: spacing[1] },
    bottom: { flexDirection: 'row', justifyContent: 'space-between' },
    stat: { alignItems: 'center', flex: 1 },
    statLabel: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: 2 },
    statValue: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
});
