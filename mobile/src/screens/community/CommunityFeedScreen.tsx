// mobile/src/screens/community/CommunityFeedScreen.tsx
// Community post feed with category filter chips, sort, and create post FAB.

import React, { useState, useCallback } from 'react';
import {
    View,
    Text,
    FlatList,
    ScrollView,
    TouchableOpacity,
    TextInput,
    Modal,
    StyleSheet,
    ActivityIndicator,
    Alert,
    RefreshControl,
    KeyboardAvoidingView,
    Platform,
    Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Plus, Heart, MessageCircle, ChevronDown, ImagePlus, X } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import {
    communityService,
    type CommunityPost,
    type PostType,
    POST_TYPE_LABELS,
    POST_TYPE_COLORS,
    formatRelativeTime,
} from '../../services/community';
import type { CommunityStackParamList } from '../../navigation/CommunityStack';

type Props = {
    navigation: NativeStackNavigationProp<CommunityStackParamList, 'CommunityFeed'>;
};

const CHIPS: { label: string; value: PostType | undefined }[] = [
    { label: 'All', value: undefined },
    { label: 'General', value: 'discussion' },
    { label: 'Tips', value: 'tip' },
    { label: 'Questions', value: 'question' },
    { label: 'Alert', value: 'alert' },
];

type SortKey = 'created_at' | 'likes_count' | 'replies_count';
const SORT_OPTIONS: { label: string; key: SortKey }[] = [
    { label: 'Most Recent', key: 'created_at' },
    { label: 'Most Upvoted', key: 'likes_count' },
    { label: 'Most Replies', key: 'replies_count' },
];

const CREATE_CATEGORIES: { label: string; value: PostType }[] = [
    { label: 'General', value: 'discussion' },
    { label: 'Tip', value: 'tip' },
    { label: 'Question', value: 'question' },
    { label: 'Alert', value: 'alert' },
];

function PostCard({ post, onPress }: { post: CommunityPost; onPress: () => void }) {
    const badgeColor = POST_TYPE_COLORS[post.post_type] ?? '#6b7280';
    return (
        <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.85}>
            <View style={styles.cardHeader}>
                <View style={[styles.badge, { backgroundColor: badgeColor + '22' }]}>
                    <Text style={[styles.badgeText, { color: badgeColor }]}>
                        {POST_TYPE_LABELS[post.post_type] ?? post.post_type}
                    </Text>
                </View>
                <Text style={styles.timestamp}>{formatRelativeTime(post.created_at)}</Text>
            </View>
            <Text style={styles.postTitle} numberOfLines={2}>{post.title}</Text>
            <View style={styles.cardFooter}>
                <Text style={styles.authorText}>{post.author_name ?? 'Farmer'}</Text>
                <View style={styles.statsRow}>
                    <Heart size={13} color={colors.muted} />
                    <Text style={styles.statText}>{post.likes_count}</Text>
                    <MessageCircle size={13} color={colors.muted} style={{ marginLeft: spacing[2] }} />
                    <Text style={styles.statText}>{post.replies_count}</Text>
                </View>
            </View>
        </TouchableOpacity>
    );
}

export function CommunityFeedScreen({ navigation }: Props) {
    const [posts, setPosts] = useState<CommunityPost[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeChip, setActiveChip] = useState<PostType | undefined>(undefined);
    const [sortKey, setSortKey] = useState<SortKey>('created_at');
    const [showSortMenu, setShowSortMenu] = useState(false);

    const [showCreate, setShowCreate] = useState(false);
    const [createTitle, setCreateTitle] = useState('');
    const [createContent, setCreateContent] = useState('');
    const [createCategory, setCreateCategory] = useState<PostType>('discussion');
    const [createErrors, setCreateErrors] = useState<Record<string, string>>({});
    const [submitting, setSubmitting] = useState(false);
    const [imageUri, setImageUri] = useState<string | null>(null);
    const [uploadingImage, setUploadingImage] = useState(false);

    const sortedPosts = [...posts].sort((a, b) => {
        if (sortKey === 'created_at') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        return (b[sortKey] as number) - (a[sortKey] as number);
    });

    const fetchPosts = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true); else setLoading(true);
        setError(null);
        try {
            const data = await communityService.listPosts({ post_type: activeChip, limit: 100 });
            setPosts(data);
        } catch {
            setError('Failed to load posts. Pull to retry.');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [activeChip]);

    React.useEffect(() => { fetchPosts(); }, [fetchPosts]);

    function validateCreate(): boolean {
        const e: Record<string, string> = {};
        if (!createTitle.trim()) e.title = 'Title is required';
        else if (createTitle.length > 200) e.title = 'Max 200 characters';
        if (!createContent.trim()) e.content = 'Content is required';
        else if (createContent.trim().length < 10) e.content = 'Min 10 characters';
        else if (createContent.length > 2000) e.content = 'Max 2000 characters';
        setCreateErrors(e);
        return Object.keys(e).length === 0;
    }

    async function handlePickImage() {
        const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (status !== 'granted') {
            Alert.alert('Permission required', 'Please allow access to your photo library.');
            return;
        }
        const result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ImagePicker.MediaTypeOptions.Images,
            allowsEditing: true,
            quality: 0.8,
        });
        if (!result.canceled && result.assets[0]) {
            setImageUri(result.assets[0].uri);
        }
    }

    async function handleCreate() {
        if (!validateCreate()) return;
        setSubmitting(true);
        try {
            let uploadedUrl: string | null = null;
            if (imageUri) {
                setUploadingImage(true);
                try {
                    uploadedUrl = await communityService.uploadImage(imageUri);
                } finally {
                    setUploadingImage(false);
                }
            }
            const post = await communityService.createPost({
                title: createTitle.trim(),
                content: createContent.trim(),
                post_type: createCategory,
                image_url: uploadedUrl,
            });
            setPosts(prev => [post, ...prev]);
            setShowCreate(false);
            setCreateTitle(''); setCreateContent(''); setCreateCategory('discussion'); setImageUri(null);
        } catch {
            Alert.alert('Error', 'Failed to create post. Please try again.');
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <SafeAreaView style={styles.safeArea}>
            <View style={styles.header}>
                <Text style={styles.headerTitle}>Community</Text>
                <TouchableOpacity style={styles.sortBtn} onPress={() => setShowSortMenu(v => !v)}>
                    <ChevronDown size={14} color={colors.primary} />
                    <Text style={styles.sortBtnText}>{SORT_OPTIONS.find(s => s.key === sortKey)?.label}</Text>
                </TouchableOpacity>
            </View>

            {showSortMenu && (
                <View style={styles.sortMenu}>
                    {SORT_OPTIONS.map(opt => (
                        <TouchableOpacity
                            key={opt.key}
                            style={[styles.sortMenuItem, opt.key === sortKey && styles.sortMenuItemActive]}
                            onPress={() => { setSortKey(opt.key); setShowSortMenu(false); }}
                        >
                            <Text style={[styles.sortMenuItemText, opt.key === sortKey && styles.sortMenuItemTextActive]}>
                                {opt.label}
                            </Text>
                        </TouchableOpacity>
                    ))}
                </View>
            )}

            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
                {CHIPS.map(chip => (
                    <TouchableOpacity
                        key={chip.label}
                        style={[styles.chip, chip.value === activeChip && styles.chipActive]}
                        onPress={() => setActiveChip(chip.value)}
                    >
                        <Text style={[styles.chipText, chip.value === activeChip && styles.chipTextActive]}>
                            {chip.label}
                        </Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            {loading ? (
                <ActivityIndicator style={{ marginTop: spacing[10] }} color={colors.primary} />
            ) : error ? (
                <View style={styles.errorState}>
                    <Text style={styles.errorStateText}>{error}</Text>
                    <TouchableOpacity onPress={() => fetchPosts()}>
                        <Text style={styles.retryText}>Retry</Text>
                    </TouchableOpacity>
                </View>
            ) : (
                <FlatList
                    data={sortedPosts}
                    keyExtractor={item => item.id}
                    renderItem={({ item }) => (
                        <PostCard post={item} onPress={() => navigation.navigate('PostDetail', { post_id: item.id })} />
                    )}
                    contentContainerStyle={styles.listContent}
                    refreshControl={
                        <RefreshControl refreshing={refreshing} onRefresh={() => fetchPosts(true)} tintColor={colors.primary} />
                    }
                    ListEmptyComponent={<Text style={styles.emptyText}>No posts yet. Be the first!</Text>}
                />
            )}

            <TouchableOpacity style={styles.fab} onPress={() => setShowCreate(true)}>
                <Plus size={24} color="#fff" />
            </TouchableOpacity>

            <Modal visible={showCreate} animationType="slide" transparent onRequestClose={() => setShowCreate(false)}>
                <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setShowCreate(false)} />
                <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.createSheet}>
                    <Text style={styles.sheetTitle}>New Post</Text>

                    <Text style={styles.createLabel}>Title</Text>
                    <TextInput
                        style={styles.createInput}
                        placeholder="What's on your mind?"
                        value={createTitle}
                        onChangeText={setCreateTitle}
                        placeholderTextColor={colors.muted}
                        maxLength={200}
                    />
                    {createErrors.title ? <Text style={styles.fieldError}>{createErrors.title}</Text> : null}

                    <Text style={styles.createLabel}>Content</Text>
                    <TextInput
                        style={[styles.createInput, styles.contentInput]}
                        placeholder="Share details…"
                        value={createContent}
                        onChangeText={setCreateContent}
                        multiline
                        textAlignVertical="top"
                        placeholderTextColor={colors.muted}
                        maxLength={2000}
                    />
                    {createErrors.content ? <Text style={styles.fieldError}>{createErrors.content}</Text> : null}

                    <Text style={styles.createLabel}>Image (optional)</Text>
                    {imageUri ? (
                        <View style={styles.imagePreviewWrapper}>
                            <Image source={{ uri: imageUri }} style={styles.imagePreview} resizeMode="cover" />
                            <TouchableOpacity style={styles.removeImageBtn} onPress={() => setImageUri(null)}>
                                <X size={14} color="#fff" />
                            </TouchableOpacity>
                        </View>
                    ) : (
                        <TouchableOpacity style={styles.imagePicker} onPress={handlePickImage}>
                            <ImagePlus size={18} color={colors.muted} />
                            <Text style={styles.imagePickerText}>Add photo</Text>
                        </TouchableOpacity>
                    )}

                    <Text style={styles.createLabel}>Category</Text>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryRow}>
                        {CREATE_CATEGORIES.map(cat => (
                            <TouchableOpacity
                                key={cat.value}
                                style={[styles.catChip, cat.value === createCategory && styles.catChipActive]}
                                onPress={() => setCreateCategory(cat.value)}
                            >
                                <Text style={[styles.catChipText, cat.value === createCategory && styles.catChipTextActive]}>
                                    {cat.label}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </ScrollView>

                    <TouchableOpacity
                        style={[styles.submitBtn, submitting && styles.submitBtnDisabled]}
                        onPress={handleCreate}
                        disabled={submitting}
                    >
                        {submitting
                            ? <><ActivityIndicator color="#fff" size="small" /><Text style={[styles.submitBtnText, { marginLeft: 8 }]}>{uploadingImage ? 'Uploading…' : 'Posting…'}</Text></>
                            : <Text style={styles.submitBtnText}>Post</Text>
                        }
                    </TouchableOpacity>
                </KeyboardAvoidingView>
            </Modal>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.background },
    header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing[4], paddingVertical: spacing[3] },
    headerTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground },
    sortBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
    sortBtnText: { fontSize: typography.fontSize.sm, color: colors.primary },
    sortMenu: { position: 'absolute', top: 56, right: spacing[4], backgroundColor: colors.card, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, zIndex: 10, ...shadows.card },
    sortMenuItem: { paddingHorizontal: spacing[4], paddingVertical: spacing[2] },
    sortMenuItemActive: { backgroundColor: colors.primaryLight },
    sortMenuItemText: { fontSize: typography.fontSize.sm, color: colors.foreground },
    sortMenuItemTextActive: { color: colors.primary, fontWeight: typography.fontWeight.medium },
    chips: { paddingHorizontal: spacing[4], gap: spacing[2], paddingBottom: spacing[2] },
    chip: { paddingHorizontal: spacing[3], paddingVertical: 6, borderRadius: radii.full, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card },
    chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
    chipText: { fontSize: typography.fontSize.sm, color: colors.muted },
    chipTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
    listContent: { padding: spacing[4], gap: spacing[3], paddingBottom: 80 },
    errorState: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[3] },
    errorStateText: { color: colors.muted, textAlign: 'center' },
    retryText: { color: colors.primary, fontWeight: typography.fontWeight.medium },
    emptyText: { textAlign: 'center', color: colors.muted, marginTop: spacing[10] },
    card: { backgroundColor: colors.card, borderRadius: radii.lg, padding: spacing[3], borderWidth: 1, borderColor: colors.border, ...shadows.sm },
    cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
    badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: radii.sm },
    badgeText: { fontSize: 11, fontWeight: typography.fontWeight.semibold },
    timestamp: { fontSize: typography.fontSize.xs, color: colors.muted },
    postTitle: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginBottom: spacing[2] },
    cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    authorText: { fontSize: typography.fontSize.xs, color: colors.muted },
    statsRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
    statText: { fontSize: typography.fontSize.xs, color: colors.muted },
    fab: { position: 'absolute', bottom: spacing[6], right: spacing[4], backgroundColor: colors.primary, width: 52, height: 52, borderRadius: 26, justifyContent: 'center', alignItems: 'center', ...shadows.modal },
    modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
    createSheet: { backgroundColor: colors.background, borderTopLeftRadius: radii.xl, borderTopRightRadius: radii.xl, padding: spacing[4], gap: spacing[2] },
    sheetTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground, marginBottom: spacing[2] },
    createLabel: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.foreground, marginBottom: 2 },
    createInput: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground, backgroundColor: colors.card },
    contentInput: { height: 100, paddingTop: spacing[2] },
    fieldError: { fontSize: typography.fontSize.xs, color: colors.error, marginTop: 2 },
    categoryRow: { gap: spacing[2] },
    catChip: { paddingHorizontal: spacing[3], paddingVertical: 6, borderRadius: radii.full, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card },
    catChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
    catChipText: { fontSize: typography.fontSize.sm, color: colors.muted },
    catChipTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
    submitBtn: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: spacing[3], alignItems: 'center', marginTop: spacing[2], flexDirection: 'row', justifyContent: 'center' },
    submitBtnDisabled: { opacity: 0.6 },
    submitBtnText: { color: '#fff', fontWeight: typography.fontWeight.semibold, fontSize: typography.fontSize.base },
    imagePicker: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, borderStyle: 'dashed', paddingVertical: spacing[3], flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing[2], backgroundColor: colors.card },
    imagePickerText: { fontSize: typography.fontSize.sm, color: colors.muted },
    imagePreviewWrapper: { position: 'relative' },
    imagePreview: { width: '100%', height: 160, borderRadius: radii.md, backgroundColor: colors.border },
    removeImageBtn: { position: 'absolute', top: spacing[2], right: spacing[2], backgroundColor: 'rgba(0,0,0,0.55)', borderRadius: 12, width: 24, height: 24, alignItems: 'center', justifyContent: 'center' },
});
