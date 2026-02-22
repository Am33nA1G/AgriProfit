import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  FlatList,
  TextInput,
  TouchableOpacity,
  Alert,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { CommunityStackParamList } from '../../types/navigation';
import { usePost, useReplies, useAddReply, useUpvotePost, useDeletePost } from '../../hooks/queries/useCommunity';
import { useAuthStore } from '../../store/authStore';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { formatRelativeTime } from '../../utils/formatting';
import type { CommunityReply } from '../../types/models';

type Props = NativeStackScreenProps<CommunityStackParamList, 'PostDetail'>;

export default function PostDetailScreen({ route, navigation }: Props) {
  const { postId } = route.params;
  const user = useAuthStore(s => s.user);
  const [replyText, setReplyText] = useState('');

  const { data: postData, isLoading } = usePost(postId);
  const { data: repliesData } = useReplies(postId);
  const addReply = useAddReply(postId);
  const upvote = useUpvotePost(postId);
  const deletePost = useDeletePost();

  const post = postData?.data;
  const replies = repliesData?.data ?? [];

  const handleUpvote = () => {
    if (!post) return;
    upvote.mutate({ action: post.user_has_upvoted ? 'remove' : 'upvote' });
  };

  const handleDelete = () => {
    Alert.alert('Delete Post', 'Are you sure you want to delete this post?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: () => {
          deletePost.mutate(postId, {
            onSuccess: () => navigation.goBack(),
          });
        },
      },
    ]);
  };

  const handleSendReply = async () => {
    const text = replyText.trim();
    if (!text) return;
    addReply.mutate(text, {
      onSuccess: () => setReplyText(''),
    });
  };

  if (isLoading || !post) return <LoadingSpinner fullScreen />;

  const isOwner = post.user_id === user?.id;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={80}
    >
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Post */}
        <View style={styles.postContainer}>
          <View style={styles.postHeader}>
            <Text style={styles.postType}>{post.post_type.toUpperCase()}</Text>
            {isOwner && (
              <TouchableOpacity onPress={handleDelete}>
                <Text style={styles.deleteBtn}>🗑 Delete</Text>
              </TouchableOpacity>
            )}
          </View>
          <Text style={styles.title}>{post.title}</Text>
          <Text style={styles.meta}>
            by {post.author_name} · {formatRelativeTime(post.created_at)}
          </Text>
          <Text style={styles.content}>{post.content}</Text>
          <TouchableOpacity style={styles.upvoteBtn} onPress={handleUpvote}>
            <Text style={[styles.upvoteText, post.user_has_upvoted && styles.upvotedText]}>
              {post.user_has_upvoted ? '👍' : '👍'} {post.upvote_count}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Replies */}
        <View style={styles.repliesSection}>
          <Text style={styles.repliesTitle}>💬 {replies.length} Replies</Text>
          {replies.map((reply: CommunityReply) => (
            <View key={reply.id} style={styles.replyCard}>
              <Text style={styles.replyAuthor}>{reply.author_name}</Text>
              <Text style={styles.replyContent}>{reply.content}</Text>
              <Text style={styles.replyMeta}>{formatRelativeTime(reply.created_at)}</Text>
            </View>
          ))}
        </View>
      </ScrollView>

      {/* Reply input */}
      <View style={styles.replyBar}>
        <TextInput
          style={styles.replyInput}
          placeholder="Write a reply..."
          placeholderTextColor={colors.text.disabled}
          value={replyText}
          onChangeText={setReplyText}
          multiline
          maxLength={500}
        />
        <TouchableOpacity
          style={[styles.sendBtn, !replyText.trim() && styles.sendBtnDisabled]}
          onPress={handleSendReply}
          disabled={!replyText.trim() || addReply.isPending}
        >
          <Text style={styles.sendBtnText}>Send</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  postContainer: {
    backgroundColor: colors.background,
    padding: spacing[4],
    marginBottom: spacing[2],
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  postHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: spacing[2] },
  postType: {
    fontSize: 10,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary[600],
    backgroundColor: colors.primary[50],
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: 4,
  },
  deleteBtn: { fontSize: typography.fontSize.sm, color: colors.error },
  title: { fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.bold, color: colors.text.primary, marginBottom: spacing[1] },
  meta: { fontSize: typography.fontSize.xs, color: colors.text.secondary, marginBottom: spacing[3] },
  content: { fontSize: typography.fontSize.base, color: colors.text.primary, lineHeight: 24, marginBottom: spacing[4] },
  upvoteBtn: { alignSelf: 'flex-start' },
  upvoteText: { fontSize: typography.fontSize.base, color: colors.text.secondary },
  upvotedText: { color: colors.primary[600], fontWeight: typography.fontWeight.bold },
  repliesSection: { paddingHorizontal: spacing[4], paddingBottom: spacing[4] },
  repliesTitle: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.text.primary, marginBottom: spacing[3] },
  replyCard: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: spacing[3],
    marginBottom: spacing[2],
    borderWidth: 1,
    borderColor: colors.border,
  },
  replyAuthor: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.text.primary, marginBottom: 2 },
  replyContent: { fontSize: typography.fontSize.sm, color: colors.text.primary, marginBottom: 4 },
  replyMeta: { fontSize: typography.fontSize.xs, color: colors.text.secondary },
  replyBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: spacing[3],
    backgroundColor: colors.background,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  replyInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    maxHeight: 100,
    fontSize: typography.fontSize.sm,
    color: colors.text.primary,
    marginRight: spacing[2],
  },
  sendBtn: {
    backgroundColor: colors.primary[600],
    borderRadius: 8,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
  },
  sendBtnDisabled: { backgroundColor: colors.gray[200] },
  sendBtnText: { color: '#fff', fontWeight: typography.fontWeight.medium, fontSize: typography.fontSize.sm },
});
