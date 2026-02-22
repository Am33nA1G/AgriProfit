import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Alert,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { CommunityStackParamList } from '../../types/navigation';
import { useCreatePost } from '../../hooks/queries/useCommunity';
import { useAuthStore } from '../../store/authStore';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

type Props = NativeStackScreenProps<CommunityStackParamList, 'CreatePost'>;

const POST_TYPES = ['discussion', 'question', 'tip'] as const;

export default function CreatePostScreen({ navigation }: Props) {
  const user = useAuthStore(s => s.user);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [postType, setPostType] = useState<'discussion' | 'question' | 'tip'>('discussion');
  const [district, setDistrict] = useState(user?.district ?? '');

  const createPost = useCreatePost();

  const handlePost = async () => {
    if (!title.trim()) { Alert.alert('Error', 'Title is required'); return; }
    if (!content.trim()) { Alert.alert('Error', 'Content is required'); return; }

    createPost.mutate(
      { title: title.trim(), content: content.trim(), post_type: postType, district: district || undefined },
      {
        onSuccess: () => navigation.goBack(),
        onError: (err: any) => {
          Alert.alert('Error', err?.response?.data?.detail ?? 'Failed to create post');
        },
      },
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        <Input
          label="Title *"
          placeholder="What's your post about?"
          value={title}
          onChangeText={t => setTitle(t.slice(0, 200))}
          editable={!createPost.isPending}
        />

        {/* Post type picker */}
        <View style={styles.field}>
          <Text style={styles.label}>Post Type</Text>
          <View style={styles.typeRow}>
            {POST_TYPES.map(type => (
              <TouchableOpacity
                key={type}
                style={[styles.typeChip, postType === type && styles.typeChipActive]}
                onPress={() => setPostType(type)}
              >
                <Text style={[styles.typeText, postType === type && styles.typeTextActive]}>
                  {type}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Content *</Text>
          <TextInput
            style={styles.contentInput}
            placeholder="Share your knowledge, question, or experience..."
            placeholderTextColor={colors.text.disabled}
            value={content}
            onChangeText={setContent}
            multiline
            numberOfLines={6}
            textAlignVertical="top"
            editable={!createPost.isPending}
          />
        </View>

        <Input
          label="District (optional)"
          placeholder="Enter district name"
          value={district}
          onChangeText={setDistrict}
          editable={!createPost.isPending}
        />

        <Button
          title="Post"
          onPress={handlePost}
          loading={createPost.isPending}
          disabled={!title.trim() || !content.trim()}
        />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: spacing[4] },
  field: { marginBottom: spacing[4] },
  label: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.text.secondary, marginBottom: spacing[2] },
  typeRow: { flexDirection: 'row', gap: spacing[2] },
  typeChip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
  },
  typeChipActive: { backgroundColor: colors.primary[600], borderColor: colors.primary[600] },
  typeText: { fontSize: typography.fontSize.sm, color: colors.text.secondary, textTransform: 'capitalize' },
  typeTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
  contentInput: {
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: 8,
    padding: spacing[3],
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
    minHeight: 120,
  },
});
