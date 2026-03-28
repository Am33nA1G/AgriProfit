// mobile/src/screens/profile/ProfileScreen.tsx
// Full-featured user profile screen.

import React, { useState, useEffect, useCallback } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    Alert,
    ScrollView,
    Modal,
    TextInput,
    ActivityIndicator,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
    User, Phone, MapPin, LogOut, Shield, ChevronRight,
    Bell, FileText, Globe, Pencil, X, Check,
} from 'lucide-react-native';
import { useAuthStore } from '../../store/authStore';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import api from '../../lib/api';

// ─── Kerala districts ──────────────────────────────────────────────────────────
const KERALA_DISTRICTS: { code: string; name: string }[] = [
    { code: 'KL-TVM', name: 'Thiruvananthapuram' },
    { code: 'KL-KLM', name: 'Kollam' },
    { code: 'KL-PTA', name: 'Pathanamthitta' },
    { code: 'KL-ALP', name: 'Alappuzha' },
    { code: 'KL-KTM', name: 'Kottayam' },
    { code: 'KL-IDK', name: 'Idukki' },
    { code: 'KL-EKM', name: 'Ernakulam' },
    { code: 'KL-TSR', name: 'Thrissur' },
    { code: 'KL-PKD', name: 'Palakkad' },
    { code: 'KL-MLP', name: 'Malappuram' },
    { code: 'KL-KKD', name: 'Kozhikode' },
    { code: 'KL-WYD', name: 'Wayanad' },
    { code: 'KL-KNR', name: 'Kannur' },
    { code: 'KL-KSD', name: 'Kasaragod' },
];

function districtName(code: string | null | undefined): string {
    if (!code) return '—';
    return KERALA_DISTRICTS.find((d) => d.code === code)?.name ?? code;
}

function memberSince(iso: string | undefined): string {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
}

// ─── Menu row ─────────────────────────────────────────────────────────────────
function MenuRow({
    icon,
    label,
    value,
    badge,
    onPress,
    danger,
    last,
}: {
    icon: React.ReactNode;
    label: string;
    value?: string;
    badge?: number;
    onPress: () => void;
    danger?: boolean;
    last?: boolean;
}) {
    return (
        <TouchableOpacity
            style={[styles.menuRow, last && styles.menuRowLast]}
            onPress={onPress}
            activeOpacity={0.7}
        >
            <View style={[styles.menuIcon, danger && styles.menuIconDanger]}>{icon}</View>
            <Text style={[styles.menuLabel, danger && styles.menuLabelDanger]}>{label}</Text>
            <View style={styles.menuRight}>
                {value ? <Text style={styles.menuValue}>{value}</Text> : null}
                {badge != null && badge > 0 ? (
                    <View style={styles.badge}>
                        <Text style={styles.badgeText}>{badge > 99 ? '99+' : badge}</Text>
                    </View>
                ) : null}
                {!danger && <ChevronRight size={16} color={colors.muted} />}
            </View>
        </TouchableOpacity>
    );
}

// ─── Main screen ──────────────────────────────────────────────────────────────
export function ProfileScreen() {
    const user = useAuthStore((s) => s.user);
    const setUser = useAuthStore((s) => s.setUser);
    const logout = useAuthStore((s) => s.logout);

    // Stats
    const [postCount, setPostCount] = useState<number | null>(null);
    const [unreadCount, setUnreadCount] = useState<number>(0);

    // Edit modal
    const [showEdit, setShowEdit] = useState(false);
    const [editName, setEditName] = useState('');
    const [editDistrict, setEditDistrict] = useState('');
    const [editLanguage, setEditLanguage] = useState<'en' | 'ml'>('en');
    const [showDistrictPicker, setShowDistrictPicker] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState<string | null>(null);

    // Notifications modal
    const [showNotifs, setShowNotifs] = useState(false);
    const [notifs, setNotifs] = useState<{ id: string; title: string; message: string; is_read: boolean; created_at: string }[]>([]);
    const [notifsLoading, setNotifsLoading] = useState(false);

    // My Posts modal
    const [showPosts, setShowPosts] = useState(false);
    const [posts, setPosts] = useState<{ id: string; title: string; post_type: string; created_at: string; likes_count: number }[]>([]);
    const [postsLoading, setPostsLoading] = useState(false);

    const fetchStats = useCallback(async () => {
        if (!user?.id) return;
        try {
            const [postsRes, unreadRes] = await Promise.all([
                api.get('/community/posts', { params: { user_id: user.id, limit: 1 } }),
                api.get('/notifications/unread-count'),
            ]);
            setPostCount(postsRes.data.total ?? 0);
            setUnreadCount(unreadRes.data.unread_count ?? 0);
        } catch {
            // non-critical
        }
    }, [user?.id]);

    useEffect(() => { fetchStats(); }, [fetchStats]);

    function openEdit() {
        setEditName(user?.name ?? '');
        setEditDistrict(user?.district ?? '');
        setEditLanguage((user as any)?.language ?? 'en');
        setSaveError(null);
        setShowEdit(true);
    }

    async function handleSave() {
        setSaving(true);
        setSaveError(null);
        try {
            const payload: Record<string, string> = {};
            if (editName.trim()) payload.name = editName.trim();
            if (editDistrict) payload.district = editDistrict;
            payload.language = editLanguage;

            const { data } = await api.put('/users/me', payload);
            setUser({ ...user!, name: data.name, district: data.district, state: data.state });
            setShowEdit(false);
        } catch (err: any) {
            setSaveError(err?.response?.data?.detail ?? 'Failed to save. Please try again.');
        } finally {
            setSaving(false);
        }
    }

    async function openNotifications() {
        setShowNotifs(true);
        setNotifsLoading(true);
        try {
            const { data } = await api.get('/notifications', { params: { limit: 50 } });
            setNotifs(data.items ?? []);
            // Mark all as read
            if ((data.unread_count ?? 0) > 0) {
                await api.put('/notifications/read-all').catch(() => {});
                setUnreadCount(0);
            }
        } catch {
            // ignore
        } finally {
            setNotifsLoading(false);
        }
    }

    async function openMyPosts() {
        if (!user?.id) return;
        setShowPosts(true);
        setPostsLoading(true);
        try {
            const { data } = await api.get('/community/posts', { params: { user_id: user.id, limit: 100 } });
            setPosts(data.items ?? []);
        } catch {
            // ignore
        } finally {
            setPostsLoading(false);
        }
    }

    function handleLogout() {
        Alert.alert('Log out', 'Are you sure you want to log out?', [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Log out', style: 'destructive', onPress: () => logout() },
        ]);
    }

    const initials = user?.name
        ? user.name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)
        : (user?.phone_number?.slice(-2) ?? '?');

    return (
        <SafeAreaView style={styles.safeArea}>
            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
                <Text style={styles.pageTitle}>Profile</Text>

                {/* ── Avatar + user header ─────────────────────────────── */}
                <View style={styles.headerCard}>
                    <View style={styles.avatar}>
                        <Text style={styles.avatarText}>{initials}</Text>
                    </View>
                    <View style={styles.headerInfo}>
                        <View style={styles.headerNameRow}>
                            <Text style={styles.name} numberOfLines={1}>
                                {user?.name ?? 'Set your name'}
                            </Text>
                            {user?.role === 'admin' && (
                                <View style={styles.adminBadge}>
                                    <Shield size={10} color={colors.primary} />
                                    <Text style={styles.adminBadgeText}>Admin</Text>
                                </View>
                            )}
                        </View>
                        <Text style={styles.phone}>{user?.phone_number ?? '—'}</Text>
                        {user?.district && (
                            <Text style={styles.location}>
                                <MapPin size={11} color={colors.muted} /> {districtName(user.district)}, Kerala
                            </Text>
                        )}
                        {(user as any)?.created_at && (
                            <Text style={styles.memberSince}>Member since {memberSince((user as any).created_at)}</Text>
                        )}
                    </View>
                </View>

                {/* ── Stats row ────────────────────────────────────────── */}
                <View style={styles.statsRow}>
                    <TouchableOpacity style={styles.statBox} onPress={openMyPosts}>
                        <Text style={styles.statNumber}>{postCount ?? '—'}</Text>
                        <Text style={styles.statLabel}>Posts</Text>
                    </TouchableOpacity>
                    <View style={styles.statDivider} />
                    <TouchableOpacity style={styles.statBox} onPress={openNotifications}>
                        <Text style={styles.statNumber}>{unreadCount}</Text>
                        <Text style={styles.statLabel}>Unread</Text>
                    </TouchableOpacity>
                    <View style={styles.statDivider} />
                    <View style={styles.statBox}>
                        <Text style={styles.statNumber}>{(user as any)?.language?.toUpperCase() ?? 'EN'}</Text>
                        <Text style={styles.statLabel}>Language</Text>
                    </View>
                </View>

                {/* ── Account section ──────────────────────────────────── */}
                <Text style={styles.sectionLabel}>Account</Text>
                <View style={styles.card}>
                    <MenuRow
                        icon={<Pencil size={16} color={colors.primary} />}
                        label="Edit Profile"
                        value={user?.name ? undefined : 'Not set'}
                        onPress={openEdit}
                    />
                    <MenuRow
                        icon={<FileText size={16} color={colors.primary} />}
                        label="My Posts"
                        value={postCount != null ? `${postCount}` : undefined}
                        onPress={openMyPosts}
                    />
                    <MenuRow
                        icon={<Bell size={16} color={colors.primary} />}
                        label="Notifications"
                        badge={unreadCount}
                        onPress={openNotifications}
                        last
                    />
                </View>

                {/* ── Preferences section ───────────────────────────────── */}
                <Text style={styles.sectionLabel}>Preferences</Text>
                <View style={styles.card}>
                    <MenuRow
                        icon={<Globe size={16} color={colors.primary} />}
                        label="Language"
                        value={(user as any)?.language === 'ml' ? 'Malayalam' : 'English'}
                        onPress={openEdit}
                        last
                    />
                </View>

                {/* ── Danger zone ───────────────────────────────────────── */}
                <View style={styles.card}>
                    <MenuRow
                        icon={<LogOut size={16} color={colors.error} />}
                        label="Log out"
                        onPress={handleLogout}
                        danger
                        last
                    />
                </View>

                <Text style={styles.version}>AgriProfit v1.0.0</Text>
            </ScrollView>

            {/* ══ Edit Profile Modal ══════════════════════════════════════ */}
            <Modal visible={showEdit} animationType="slide" transparent onRequestClose={() => setShowEdit(false)}>
                <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowEdit(false)} />
                <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.sheet}>
                    <View style={styles.sheetHeader}>
                        <Text style={styles.sheetTitle}>Edit Profile</Text>
                        <TouchableOpacity onPress={() => setShowEdit(false)}>
                            <X size={20} color={colors.muted} />
                        </TouchableOpacity>
                    </View>

                    <Text style={styles.fieldLabel}>Name</Text>
                    <TextInput
                        style={styles.input}
                        value={editName}
                        onChangeText={setEditName}
                        placeholder="Your full name"
                        placeholderTextColor={colors.muted}
                        maxLength={100}
                    />

                    <Text style={styles.fieldLabel}>District</Text>
                    <TouchableOpacity style={styles.selectRow} onPress={() => setShowDistrictPicker(true)}>
                        <Text style={editDistrict ? styles.selectValue : styles.selectPlaceholder}>
                            {editDistrict ? districtName(editDistrict) : 'Select district'}
                        </Text>
                        <ChevronRight size={16} color={colors.muted} />
                    </TouchableOpacity>

                    <Text style={styles.fieldLabel}>Language</Text>
                    <View style={styles.langRow}>
                        {(['en', 'ml'] as const).map((lang) => (
                            <TouchableOpacity
                                key={lang}
                                style={[styles.langBtn, editLanguage === lang && styles.langBtnActive]}
                                onPress={() => setEditLanguage(lang)}
                            >
                                <Text style={[styles.langBtnText, editLanguage === lang && styles.langBtnTextActive]}>
                                    {lang === 'en' ? 'English' : 'Malayalam'}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </View>

                    {saveError ? <Text style={styles.errorText}>{saveError}</Text> : null}

                    <TouchableOpacity
                        style={[styles.saveBtn, saving && { opacity: 0.6 }]}
                        onPress={handleSave}
                        disabled={saving}
                    >
                        {saving
                            ? <ActivityIndicator color="#fff" size="small" />
                            : <><Check size={16} color="#fff" /><Text style={styles.saveBtnText}>Save Changes</Text></>
                        }
                    </TouchableOpacity>
                </KeyboardAvoidingView>
            </Modal>

            {/* ══ District Picker Modal ══════════════════════════════════ */}
            <Modal visible={showDistrictPicker} animationType="slide" transparent onRequestClose={() => setShowDistrictPicker(false)}>
                <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowDistrictPicker(false)} />
                <View style={[styles.sheet, { maxHeight: '70%' }]}>
                    <View style={styles.sheetHeader}>
                        <Text style={styles.sheetTitle}>Select District</Text>
                        <TouchableOpacity onPress={() => setShowDistrictPicker(false)}>
                            <X size={20} color={colors.muted} />
                        </TouchableOpacity>
                    </View>
                    <ScrollView>
                        {KERALA_DISTRICTS.map((d) => (
                            <TouchableOpacity
                                key={d.code}
                                style={[styles.districtRow, editDistrict === d.code && styles.districtRowActive]}
                                onPress={() => { setEditDistrict(d.code); setShowDistrictPicker(false); }}
                            >
                                <Text style={[styles.districtRowText, editDistrict === d.code && styles.districtRowTextActive]}>
                                    {d.name}
                                </Text>
                                {editDistrict === d.code && <Check size={16} color={colors.primary} />}
                            </TouchableOpacity>
                        ))}
                    </ScrollView>
                </View>
            </Modal>

            {/* ══ Notifications Modal ════════════════════════════════════ */}
            <Modal visible={showNotifs} animationType="slide" transparent onRequestClose={() => setShowNotifs(false)}>
                <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowNotifs(false)} />
                <View style={[styles.sheet, { maxHeight: '75%' }]}>
                    <View style={styles.sheetHeader}>
                        <Text style={styles.sheetTitle}>Notifications</Text>
                        <TouchableOpacity onPress={() => setShowNotifs(false)}>
                            <X size={20} color={colors.muted} />
                        </TouchableOpacity>
                    </View>
                    {notifsLoading ? (
                        <ActivityIndicator style={{ marginTop: spacing[6] }} color={colors.primary} />
                    ) : notifs.length === 0 ? (
                        <Text style={styles.emptyText}>No notifications yet</Text>
                    ) : (
                        <ScrollView>
                            {notifs.map((n) => (
                                <View key={n.id} style={[styles.notifRow, !n.is_read && styles.notifRowUnread]}>
                                    {!n.is_read && <View style={styles.unreadDot} />}
                                    <View style={{ flex: 1 }}>
                                        <Text style={styles.notifTitle}>{n.title}</Text>
                                        <Text style={styles.notifMessage} numberOfLines={2}>{n.message}</Text>
                                    </View>
                                </View>
                            ))}
                        </ScrollView>
                    )}
                </View>
            </Modal>

            {/* ══ My Posts Modal ═════════════════════════════════════════ */}
            <Modal visible={showPosts} animationType="slide" transparent onRequestClose={() => setShowPosts(false)}>
                <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowPosts(false)} />
                <View style={[styles.sheet, { maxHeight: '75%' }]}>
                    <View style={styles.sheetHeader}>
                        <Text style={styles.sheetTitle}>My Posts</Text>
                        <TouchableOpacity onPress={() => setShowPosts(false)}>
                            <X size={20} color={colors.muted} />
                        </TouchableOpacity>
                    </View>
                    {postsLoading ? (
                        <ActivityIndicator style={{ marginTop: spacing[6] }} color={colors.primary} />
                    ) : posts.length === 0 ? (
                        <Text style={styles.emptyText}>No posts yet</Text>
                    ) : (
                        <ScrollView>
                            {posts.map((p) => (
                                <View key={p.id} style={styles.postRow}>
                                    <View style={styles.postTypeBadge}>
                                        <Text style={styles.postTypeBadgeText}>{p.post_type}</Text>
                                    </View>
                                    <View style={{ flex: 1 }}>
                                        <Text style={styles.postTitle} numberOfLines={2}>{p.title}</Text>
                                        <Text style={styles.postMeta}>
                                            {new Date(p.created_at).toLocaleDateString('en-IN')} · {p.likes_count} likes
                                        </Text>
                                    </View>
                                </View>
                            ))}
                        </ScrollView>
                    )}
                </View>
            </Modal>
        </SafeAreaView>
    );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.surface },
    content: { padding: spacing[4], gap: spacing[3], paddingBottom: spacing[8] },
    pageTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground },

    // Header card
    headerCard: { backgroundColor: colors.card, borderRadius: radii.lg, padding: spacing[4], flexDirection: 'row', alignItems: 'center', gap: spacing[3], borderWidth: 1, borderColor: colors.border, ...shadows.sm },
    avatar: { width: 60, height: 60, borderRadius: 30, backgroundColor: colors.primaryLight, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
    avatarText: { fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.bold, color: colors.primary },
    headerInfo: { flex: 1, gap: 2 },
    headerNameRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
    name: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.bold, color: colors.foreground, flexShrink: 1 },
    adminBadge: { flexDirection: 'row', alignItems: 'center', gap: 3, backgroundColor: colors.primaryLight, paddingHorizontal: 6, paddingVertical: 2, borderRadius: radii.full },
    adminBadgeText: { fontSize: 10, color: colors.primary, fontWeight: typography.fontWeight.semibold },
    phone: { fontSize: typography.fontSize.sm, color: colors.muted },
    location: { fontSize: typography.fontSize.xs, color: colors.muted },
    memberSince: { fontSize: typography.fontSize.xs, color: colors.mutedLight, marginTop: 2 },

    // Stats row
    statsRow: { backgroundColor: colors.card, borderRadius: radii.lg, flexDirection: 'row', borderWidth: 1, borderColor: colors.border, ...shadows.sm },
    statBox: { flex: 1, alignItems: 'center', paddingVertical: spacing[3] },
    statDivider: { width: 1, backgroundColor: colors.border, marginVertical: spacing[2] },
    statNumber: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground },
    statLabel: { fontSize: typography.fontSize.xs, color: colors.muted, marginTop: 2 },

    // Section
    sectionLabel: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold, color: colors.muted, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: -spacing[1] },

    // Card + menu rows
    card: { backgroundColor: colors.card, borderRadius: radii.lg, borderWidth: 1, borderColor: colors.border, overflow: 'hidden', ...shadows.sm },
    menuRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: spacing[4], paddingVertical: spacing[3], borderBottomWidth: 1, borderBottomColor: colors.border },
    menuRowLast: { borderBottomWidth: 0 },
    menuIcon: { width: 32, height: 32, borderRadius: radii.md, backgroundColor: colors.primaryLight, alignItems: 'center', justifyContent: 'center', marginRight: spacing[3] },
    menuIconDanger: { backgroundColor: colors.errorLight },
    menuLabel: { flex: 1, fontSize: typography.fontSize.base, color: colors.foreground },
    menuLabelDanger: { color: colors.error },
    menuRight: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
    menuValue: { fontSize: typography.fontSize.sm, color: colors.muted },
    badge: { backgroundColor: colors.error, borderRadius: radii.full, minWidth: 20, height: 20, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 4 },
    badgeText: { fontSize: 11, color: '#fff', fontWeight: typography.fontWeight.bold },

    version: { textAlign: 'center', fontSize: typography.fontSize.xs, color: colors.mutedLight, marginTop: spacing[2] },

    // Modal shared
    overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
    sheet: { backgroundColor: colors.background, borderTopLeftRadius: radii.xl, borderTopRightRadius: radii.xl, padding: spacing[4], gap: spacing[3] },
    sheetHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    sheetTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground },
    emptyText: { textAlign: 'center', color: colors.muted, marginVertical: spacing[8] },

    // Edit profile
    fieldLabel: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.foreground, marginBottom: 2 },
    input: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground, backgroundColor: colors.card },
    selectRow: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], backgroundColor: colors.card, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
    selectValue: { fontSize: typography.fontSize.base, color: colors.foreground },
    selectPlaceholder: { fontSize: typography.fontSize.base, color: colors.muted },
    langRow: { flexDirection: 'row', gap: spacing[2] },
    langBtn: { flex: 1, paddingVertical: spacing[2], borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, alignItems: 'center', backgroundColor: colors.card },
    langBtnActive: { backgroundColor: colors.primaryLight, borderColor: colors.primary },
    langBtnText: { fontSize: typography.fontSize.sm, color: colors.muted, fontWeight: typography.fontWeight.medium },
    langBtnTextActive: { color: colors.primary },
    errorText: { fontSize: typography.fontSize.sm, color: colors.error },
    saveBtn: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: spacing[3], alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: spacing[2] },
    saveBtnText: { color: '#fff', fontWeight: typography.fontWeight.semibold, fontSize: typography.fontSize.base },

    // District picker
    districtRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing[4], paddingVertical: spacing[3], borderBottomWidth: 1, borderBottomColor: colors.border },
    districtRowActive: { backgroundColor: colors.primaryLight },
    districtRowText: { fontSize: typography.fontSize.base, color: colors.foreground },
    districtRowTextActive: { color: colors.primary, fontWeight: typography.fontWeight.medium },

    // Notifications
    notifRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing[2], paddingHorizontal: spacing[4], paddingVertical: spacing[3], borderBottomWidth: 1, borderBottomColor: colors.border },
    notifRowUnread: { backgroundColor: colors.primaryLight + '55' },
    unreadDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.primary, marginTop: 5, flexShrink: 0 },
    notifTitle: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    notifMessage: { fontSize: typography.fontSize.xs, color: colors.muted, marginTop: 2 },

    // My posts
    postRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing[3], paddingHorizontal: spacing[4], paddingVertical: spacing[3], borderBottomWidth: 1, borderBottomColor: colors.border },
    postTypeBadge: { backgroundColor: colors.primaryLight, borderRadius: radii.sm, paddingHorizontal: 6, paddingVertical: 2, alignSelf: 'flex-start', marginTop: 2 },
    postTypeBadgeText: { fontSize: 10, color: colors.primary, fontWeight: typography.fontWeight.semibold, textTransform: 'capitalize' },
    postTitle: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.foreground },
    postMeta: { fontSize: typography.fontSize.xs, color: colors.muted, marginTop: 2 },
});
