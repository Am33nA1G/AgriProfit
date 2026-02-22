import React, { useRef, useEffect, useState } from 'react';
import { View, TextInput, StyleSheet, NativeSyntheticEvent, TextInputKeyPressEventData } from 'react-native';
import { colors } from '../../theme/colors';
import { typography } from '../../theme/typography';
import { spacing } from '../../theme/spacing';
import { OTP_LENGTH } from '../../utils/constants';

interface OTPInputProps {
  onChange: (code: string) => void;
  value?: string;
  length?: number;
  disabled?: boolean;
}

export default function OTPInput({
  onChange,
  value,
  length = OTP_LENGTH,
  disabled = false,
}: OTPInputProps) {
  const [digits, setDigits] = useState<string[]>(() => {
    if (value) {
      return value.split('').slice(0, length).concat(Array(Math.max(0, length - value.length)).fill(''));
    }
    return Array(length).fill('');
  });
  const inputRefs = useRef<(TextInput | null)[]>([]);

  // Sync external value changes
  useEffect(() => {
    if (value !== undefined) {
      const newDigits = value.split('').slice(0, length).concat(Array(Math.max(0, length - value.length)).fill(''));
      setDigits(newDigits);
    }
  }, [value, length]);

  const handleChange = (text: string, index: number) => {
    // Handle paste of full OTP
    if (text.length === length && /^\d+$/.test(text)) {
      const newDigits = text.split('');
      setDigits(newDigits);
      onChange(text);
      inputRefs.current[length - 1]?.blur();
      return;
    }

    const digit = text.slice(-1);
    if (!/^\d?$/.test(digit)) return;

    const newDigits = [...digits];
    newDigits[index] = digit;
    setDigits(newDigits);

    const code = newDigits.join('');
    onChange(code);

    // Auto-advance to next input
    if (digit && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all filled
    if (code.length === length && !code.includes('')) {
      inputRefs.current[index]?.blur();
    }
  };

  const handleKeyPress = (
    e: NativeSyntheticEvent<TextInputKeyPressEventData>,
    index: number,
  ) => {
    if (e.nativeEvent.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  return (
    <View style={styles.container}>
      {digits.map((digit, index) => (
        <TextInput
          key={index}
          testID={`otp-input-${index}`}
          ref={ref => {
            inputRefs.current[index] = ref;
          }}
          style={[styles.input, digit ? styles.inputFilled : null]}
          value={digit}
          onChangeText={text => handleChange(text, index)}
          onKeyPress={e => handleKeyPress(e, index)}
          keyboardType="numeric"
          maxLength={length}
          editable={!disabled}
          selectTextOnFocus
          textContentType="oneTimeCode"
          autoComplete="one-time-code"
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing[2],
  },
  input: {
    width: 44,
    height: 52,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: 8,
    textAlign: 'center',
    fontSize: typography.fontSize.xl,
    fontWeight: typography.fontWeight.bold,
    color: colors.text.primary,
    backgroundColor: colors.background,
  },
  inputFilled: {
    borderColor: colors.primary[600],
    backgroundColor: colors.primary[50],
  },
});
