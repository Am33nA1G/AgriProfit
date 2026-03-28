// mobile/src/screens/community/PostDetailScreen.tsx
// Full post view with upvote toggle, replies, and owner edit/delete.

import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    ScrollView,
    TextInput,
    TouchableOpacity,
    Image,
    StyleSheet,
    ActivityIndicator,
    Alert,
    KeyboardAvoidingView,
    Platform,
    ActionSheetIOS,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Heart, MessageCircle, MoreVertical, Send } from 'lucide-react-native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import {
    communityService,
    type CommunityPost,
    type CommunityReply,
    type PostType,
    POST_TYPE_LABELS,
    POST_TYPE_COLORS,
    formatRelativeTime,
} from '../../services/community';
import { useAuthStore } from '../../store/authStore';
import api from '../../lib/api';
import type { CommunityStackParamList } from '../../navigation/CommunityStack';

type Props = {
    navigation: NativeStackNavigationProp<CommunityStackParamList, 'PostDetail'>;
    route: RouteProp<CommunityStackParamList, 'PostDetail'>;
};

const CREATE_CATEGORIES: { label: string; value: PostType }[] = [
    { label: 'General', value: 'discussion' },
    { label: 'Tip', value: 'tip' },
    { label: 'Question', value: 'question' },
    { label: 'Alert', value: 'alert' },
];

export function PostDetailScreen({ navigation, route }: Props) {
    const { post_id } = route.params;
    const currentUserId = useAuthStore(s => s.user?.id);

    const [post, setPost] = useState<CommunityPost | null>(null);
    const [replies, setReplies] = useState<CommunityReply[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [liked, setLiked] = useState(false);
    const [likesCount, setLikesCount] = useState(0);
    const [replyText, setReplyText] = useState('');
    const [submittingReply, setSubmittingReply] = useState(false);

    // Edit state
    const [editTitle, setEditTitle] = useState('');
    const [editContent, setEditContent] = useState('');
    const [editCategory, setEditCategory] = useState<PostType>('discussion');
    const [showEditSheet, setShowEditSheet] = useState(false);
    const [submittingEdit, setSubmittingEdit] = useState(false);

    useEffect(() => { loadPost(); }, [post_id]);

    async function loadPost() {
        setLoading(true);
        setError(null);
        try {
            const [fetchedPost, fetchedReplies] = await Promise.all([
                api.get(`/community/posts/${post_id}`).then(r => r.data as CommunityPost),
                communityService.getReplies(post_id),
            ]);
            setPost(fetchedPost);
            setLiked(fetchedPost.user_has_liked);
            setLikesCount(fetchedPost.likes_count);
            setReplies(fetchedReplies);
        } catch {
            setError('Failed to load post.');
        } finally {
            setLoading(false);
        }
    }

    async function handleUpvote() {
        if (!post) return;
        const prevLiked = liked;
        const prevCount = likesCount;
        setLiked(!liked);
        setLikesCount(c => prevLiked ? c - 1 : c + 1);
        try {
            if (prevLiked) await communityService.removeUpvote(post_id);
            else await communityService.addUpvote(post_id);
        } catch {
            setLiked(prevLiked);
            setLikesCount(prevCount);
            Alert.alert('Failed to update');
        }
    }

    async function handleAddReply() {
        if (!replyText.trim()) return;
        setSubmittingReply(true);
        try {
            const reply = await communityService.addReply(post_id, replyText.trim());
            setReplies(prev => [...prev, reply]);
            setReplyText('');
        } catch {
            Alert.alert('Error', 'Failed to post reply.');
        } finally {
            setSubmittingReply(false);
        }
    }

    function openOwnerMenu() {
        if (Platform.OS === 'ios') {
            ActionSheetIOS.showActionSheetWithOptions(
                { options: ['Cancel', 'Edit', 'Delete'], cancelButtonIndex: 0, destructiveButtonIndex: 2 },
                idx => { if (idx === 1) openEdit(); if (idx === 2) confirmDelete(); }
            );
        } else {
            Alert.alert('Post Options', undefined, [
                { text: 'Edit', onPress: openEdit },
                { text: 'Delete', style: 'destructive', onPress: confirmDelete },
                { text: 'Cancel', style: 'cancel' },
            ]);
        }
    }

    function openEdit() {
        if (!post) return;
        setEditTitle(post.title);
        setEditContent(post.content);
        setEditCategory(post.post_type);
        setShowEditSheet(true);
    }

    async function handleEdit() {
        if (!editTitle.trim() || editContent.trim().length < 10) {
            Alert.alert('Validation', 'Title and content (min 10 chars) are required.');
            return;
        }
        setSubmittingEdit(true);
        try {
            const updated = await communityService.updatePost(post_id, {
                title: editTitle.trim(),
                content: editContent.trim(),
                post_type: editCategory,
            });
            setPost(updated);
            setShowEditSheet(false);
        } catch {
            Alert.alert('Error', 'Failed to update post.');
        } finally {
            setSubmittingEdit(false);
        }
    }

    function confirmDelete() {
        Alert.alert('Delete Post', 'Are you sure?', [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Delete', style: 'destructive', onPress: async () => {
                try {
                    await communityService.deletePost(post_id);
                    navigation.goBack();
                } catch {
                    Alert.alert('Error', 'Failed to delete post.');
                }
            }},
        ]);
    }

    // Register ⋮ header button once post loads
    useEffect(() => {
        if (post && currentUserId && post.user_id === currentUserId) {
            navigation.setOptions({
                headerRight: () => (
                    <TouchableOpacity onPress={openOwnerMenu} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
                        <MoreVertical size={20} color={colors.foreground} />
                    </TouchableOpacity>
                ),
            });
        }
    }, [post, currentUserId]);

    if (loading) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <ActivityIndicator style={{ marginTop: spacing[10] }} color={colors.primary} />
            </SafeAreaView>
        );
    }

    if (error || !post) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <Text style={styles.errorText}>{error ?? 'Post not found.'}</Text>
            </SafeAreaView>
        );
    }

    const badgeColor = POST_TYPE_COLORS[post.post_type] ?? '#6b7280';

    return (
        <SafeAreaView style={styles.safeArea} edges={['bottom']}>
            <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
                <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
                    <View style={[styles.badge, { backgroundColor: badgeColor + '22', alignSelf: 'flex-start', marginBottom: spacing[2] }]}>
                        <Text style={[styles.badgeText, { color: badgeColor }]}>
                            {POST_TYPE_LABELS[post.post_type]}
                        </Text>
                    </View>
                    <Text style={styles.postTitle}>{post.title}</Text>
                    <Text style={styles.postMeta}>{post.author_name ?? 'Farmer'} · {formatRelativeTime(post.created_at)}</Text>
                    <Text style={styles.postContent}>{post.content}</Text>

                    {post.image_url ? (
                        <Image source={{ uri: post.image_url }} style={styles.postImage} resizeMode="cover" />
                    ) : null}

                    <TouchableOpacity style={styles.upvoteBtn} onPress={handleUpvote}>
                        <Heart
                            size={18}
                            color={liked ? colors.error : colors.muted}
                            fill={liked ? colors.error : 'none'}
                        />
                        <Text style={[styles.upvoteCount, liked && { color: colors.error }]}>{likesCount}</Text>
                    </TouchableOpacity>

                    <View style={styles.repliesDivider}>
                        <MessageCircle size={14} color={colors.muted} />
                        <Text style={styles.repliesHeader}>{replies.length} {replies.length === 1 ? 'reply' : 'replies'}</Text>
                    </View>

                    {replies.map(reply => (
                        <View key={reply.id} style={styles.replyCard}>
                            <Text style={styles.replyAuthor}>{reply.author_name ?? 'Farmer'}</Text>
                            <Text style={styles.replyContent}>{reply.content}</Text>
                            <Text style={styles.replyTime}>{formatRelativeTime(reply.created_at)}</Text>
                        </View>
                    ))}
                </ScrollView>

                <View style={styles.replyBar}>
                    <TextInput
                        style={styles.replyInput}
                        placeholder="Write a reply…"
                        value={replyText}
                        onChangeText={setReplyText}
                        placeholderTextColor={colors.muted}
                        multiline
                    />
                    <TouchableOpacity
                        style={[styles.sendBtn, (!replyText.trim() || submittingReply) && styles.sendBtnDisabled]}
                        onPress={handleAddReply}
                        disabled={!replyText.trim() || submittingReply}
                    >
                        {submittingReply
                            ? <ActivityIndicator size="small" color="#fff" />
                            : <Send size={16} color="#fff" />
                        }
                    </TouchableOpacity>
                </View>
            </KeyboardAvoidingView>

            {/* Edit sheet */}
            {showEditSheet && (
                <View style={StyleSheet.absoluteFillObject as object}>
                    <TouchableOpacity style={styles.editBackdrop} activeOpacity={1} onPress={() => setShowEditSheet(false)} />
                    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.editSheet}>
                        <Text style={styles.sheetTitle}>Edit Post</Text>
                        <TextInput style={styles.editInput} value={editTitle} onChangeText={setEditTitle} placeholder="Title" placeholderTextColor={colors.muted} />
                        <TextInput style={[styles.editInput, styles.editContentInput]} value={editContent} onChangeText={setEditContent} multiline textAlignVertical="top" placeholder="Content" placeholderTextColor={colors.muted} />
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryRow}>
                            {CREATE_CATEGORIES.map(cat => (
                                <TouchableOpacity key={cat.value} style={[styles.catChip, cat.value === editCategory && styles.catChipActive]} onPress={() => setEditCategory(cat.value)}>
                                    <Text style={[styles.catChipText, cat.value === editCategory && styles.catChipTextActive]}>{cat.label}</Text>
                                </TouchableOpacity>
                            ))}
                        </ScrollView>
                        <TouchableOpacity style={[styles.submitBtn, submittingEdit && styles.submitBtnDisabled]} onPress={handleEdit} disabled={submittingEdit}>
                            {submittingEdit ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.submitBtnText}>Save</Text>}
                        </TouchableOpacity>
                    </KeyboardAvoidingView>
                </View>
            )}
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.background },
    scroll: { flex: 1 },
    scrollContent: { padding: spacing[4], paddingBottom: spacing[8] },
    badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: radii.sm },
    badgeText: { fontSize: 11, fontWeight: typography.fontWeight.semibold },
    postTitle: { fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.bold, color: colors.foreground, marginBottom: 4 },
    postMeta: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: spacing[3] },
    postContent: { fontSize: typography.fontSize.base, color: colors.foreground, lineHeight: 22, marginBottom: spacing[3] },
    postImage: { width: '100%', height: 200, borderRadius: radii.lg, marginBottom: spacing[3] },
    upvoteBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', paddingVertical: spacing[2], marginBottom: spacing[4] },
    upvoteCount: { fontSize: typography.fontSize.base, color: colors.muted, fontWeight: typography.fontWeight.medium },
    repliesDivider: { flexDirection: 'row', alignItems: 'center', gap: 6, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: spacing[3], marginBottom: spacing[3] },
    repliesHeader: { fontSize: typography.fontSize.sm, color: colors.muted, fontWeight: typography.fontWeight.medium },
    replyCard: { backgroundColor: colors.surface, borderRadius: radii.md, padding: spacing[3], marginBottom: spacing[2], borderWidth: 1, borderColor: colors.border },
    replyAuthor: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginBottom: 2 },
    replyContent: { fontSize: typography.fontSize.base, color: colors.foreground },
    replyTime: { fontSize: typography.fontSize.xs, color: colors.muted, marginTop: 4 },
    replyBar: { flexDirection: 'row', alignItems: 'flex-end', gap: spacing[2], padding: spacing[3], borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.background },
    replyInput: { flex: 1, borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground, backgroundColor: colors.card, maxHeight: 80 },
    sendBtn: { backgroundColor: colors.primary, width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center' },
    sendBtnDisabled: { opacity: 0.4 },
    errorText: { color: colors.error, textAlign: 'center', marginTop: spacing[10] },
    editBackdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
    editSheet: { backgroundColor: colors.background, borderTopLeftRadius: radii.xl, borderTopRightRadius: radii.xl, padding: spacing[4], gap: spacing[2] },
    sheetTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground, marginBottom: spacing[2] },
    editInput: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground, backgroundColor: colors.card },
    editContentInput: { height: 100, paddingTop: spacing[2] },
    categoryRow: { gap: spacing[2] },
    catChip: { paddingHorizontal: spacing[3], paddingVertical: 6, borderRadius: radii.full, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card },
    catChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
    catChipText: { fontSize: typography.fontSize.sm, color: colors.muted },
    catChipTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
    submitBtn: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: spacing[3], alignItems: 'center', marginTop: spacing[2] },
    submitBtnDisabled: { opacity: 0.6 },
    submitBtnText: { color: '#fff', fontWeight: typography.fontWeight.semibold, fontSize: typography.fontSize.base },
    shadows: { ...shadows.sm },
});
