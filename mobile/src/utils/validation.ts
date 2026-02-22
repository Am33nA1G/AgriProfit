/**
 * Validate Indian mobile phone number
 * Must be 10 digits starting with 6, 7, 8, or 9
 */
export function validatePhoneNumber(phone: string): boolean {
  const cleaned = phone.replace(/\D/g, '');
  return /^[6-9][0-9]{9}$/.test(cleaned);
}

/**
 * Validate OTP is exactly 6 digits
 */
export function validateOTP(otp: string): boolean {
  return /^\d{6}$/.test(otp);
}
