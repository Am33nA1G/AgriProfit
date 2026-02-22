import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AdminStackParamList } from '../../types/navigation';
import { useAdminBroadcast } from '../../hooks/queries/useAdmin';
import Button from '../../components/ui/Button';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';

type Props = NativeStackScreenProps<AdminStackParamList, 'Broadcast'>;

const DISTRICTS = [
  'All Users',
  'Delhi',
  'Mumbai',
  'Pune',
  'Bangalore',
  'Hyderabad',
  'Chennai',
  'Kolkata',
  'Ahmedabad',
  'Jaipur',
  'Lucknow',
];

const NOTIFICATION_TYPES = [
  { value: 'announcement', label: '📢 Announcement' },
  { value: 'price_alert', label: '💰 Price Alert' },
  { value: 'system', label: 'ℹ️ System' },
];

export default function BroadcastScreen({ navigation }: Props) {
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [targetDistrict, setTargetDistrict] = useState('All Users');
  const [notificationType, setNotificationType] = useState('announcement');

  const broadcast = useAdminBroadcast();

  const handleSend = () => {
    if (!title.trim()) {
      Alert.alert('Validation Error', 'Title is required');
      return;
    }
    if (!message.trim()) {
      Alert.alert('Validation Error', 'Message is required');
      return;
    }

    Alert.alert(
      'Confirm Broadcast',
      `Send "${title}" to ${targetDistrict === 'All Users' ? 'all users' : targetDistrict + ' district'}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Send',
          style: 'destructive',
          onPress: () => {
            broadcast.mutate(
              {
                title: title.trim(),
                message: message.trim(),
                target_district: targetDistrict === 'All Users' ? undefined : targetDistrict,
                notification_type: notificationType,
              },
              {
                onSuccess: () => {
                  Alert.alert('Success', 'Broadcast sent successfully', [
                    { text: 'OK', onPress: () => navigation.goBack() },
                  ]);
                },
                onError: () => {
                  Alert.alert('Error', 'Failed to send broadcast. Please try again.');
                },
              },
            );
          },
        },
      ],
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text style={styles.sectionTitle}>Notification Type</Text>
      <View style={styles.chipRow}>
        {NOTIFICATION_TYPES.map(({ value, label }) => (
          <TouchableOpacity
            key={value}
            style={[styles.chip, notificationType === value && styles.chipSelected]}
            onPress={() => setNotificationType(value)}
          >
            <Text style={[styles.chipText, notificationType === value && styles.chipTextSelected]}>
              {label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Title *</Text>
      <TextInput
        style={styles.input}
        value={title}
        onChangeText={setTitle}
        placeholder="Enter broadcast title"
        placeholderTextColor={colors.text.secondary}
        maxLength={100}
      />
      <Text style={styles.charCount}>{title.length}/100</Text>

      <Text style={styles.label}>Message *</Text>
      <TextInput
        style={[styles.input, styles.messageInput]}
        value={message}
        onChangeText={setMessage}
        placeholder="Enter broadcast message"
        placeholderTextColor={colors.text.secondary}
        multiline
        numberOfLines={5}
        textAlignVertical="top"
        maxLength={500}
      />
      <Text style={styles.charCount}>{message.length}/500</Text>

      <Text style={styles.sectionTitle}>Target Audience</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.districtScroll}>
        <View style={styles.districtRow}>
          {DISTRICTS.map(district => (
            <TouchableOpacity
              key={district}
              style={[styles.districtChip, targetDistrict === district && styles.chipSelected]}
              onPress={() => setTargetDistrict(district)}
            >
              <Text style={[styles.chipText, targetDistrict === district && styles.chipTextSelected]}>
                {district}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>

      <View style={styles.previewBox}>
        <Text style={styles.previewTitle}>Preview</Text>
        <Text style={styles.previewHeading}>{title || 'Title will appear here'}</Text>
        <Text style={styles.previewMessage}>{message || 'Message will appear here'}</Text>
        <Text style={styles.previewTarget}>
          → {targetDistrict === 'All Users' ? 'All Users' : `${targetDistrict} district only`}
        </Text>
      </View>

      <Button
        title="Send Broadcast"
        onPress={handleSend}
        loading={broadcast.isPending}
        style={styles.sendBtn}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing[4], paddingBottom: spacing[8] },
  sectionTitle: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text.primary,
    marginBottom: spacing[2],
    marginTop: spacing[4],
  },
  label: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.text.primary,
    marginBottom: spacing[1],
    marginTop: spacing[3],
  },
  input: {
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: spacing[3],
    fontSize: typography.fontSize.base,
    color: colors.text.primary,
  },
  messageInput: {
    height: 120,
    paddingTop: spacing[3],
  },
  charCount: {
    fontSize: typography.fontSize.xs,
    color: colors.text.secondary,
    textAlign: 'right',
    marginTop: 4,
  },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  chip: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.background,
  },
  chipSelected: {
    backgroundColor: colors.primary[600],
    borderColor: colors.primary[600],
  },
  chipText: { fontSize: typography.fontSize.sm, color: colors.text.secondary },
  chipTextSelected: { color: '#fff', fontWeight: typography.fontWeight.medium },
  districtScroll: { marginBottom: spacing[2] },
  districtRow: { flexDirection: 'row', gap: spacing[2], paddingBottom: spacing[2] },
  districtChip: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.background,
  },
  previewBox: {
    backgroundColor: colors.primary[50],
    borderRadius: 12,
    padding: spacing[4],
    marginTop: spacing[4],
    borderLeftWidth: 4,
    borderLeftColor: colors.primary[500],
  },
  previewTitle: {
    fontSize: typography.fontSize.xs,
    color: colors.primary[600],
    fontWeight: typography.fontWeight.semibold,
    marginBottom: spacing[2],
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  previewHeading: {
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.bold,
    color: colors.text.primary,
    marginBottom: spacing[1],
  },
  previewMessage: {
    fontSize: typography.fontSize.sm,
    color: colors.text.secondary,
    marginBottom: spacing[2],
  },
  previewTarget: {
    fontSize: typography.fontSize.xs,
    color: colors.primary[600],
  },
  sendBtn: { marginTop: spacing[6] },
});
