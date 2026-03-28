import { describe, it, expect } from 'vitest';

// Form validation utilities
export const validatePhone = (phone: string): boolean => {
  return /^[0-9]{10}$/.test(phone);
};

export const validateEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

export const validateOTP = (otp: string): boolean => {
  return /^[0-9]{6}$/.test(otp);
};

export const validateRequired = (value: string): boolean => {
  return value.trim().length > 0;
};

export const validateKeralaDistrict = (district: string): boolean => {
  const keralaDistricts = [
    'Thiruvananthapuram', 'Kollam', 'Pathanamthitta', 'Alappuzha', 
    'Kottayam', 'Idukki', 'Ernakulam', 'Thrissur', 'Palakkad', 
    'Malappuram', 'Kozhikode', 'Wayanad', 'Kannur', 'Kasaragod'
  ];
  return keralaDistricts.includes(district);
};

describe('Form Validation Utilities', () => {
  describe('validatePhone', () => {
    it('should accept valid 10-digit phone number', () => {
      expect(validatePhone('9876543210')).toBe(true);
      expect(validatePhone('1234567890')).toBe(true);
    });

    it('should reject phone with less than 10 digits', () => {
      expect(validatePhone('123456789')).toBe(false);
      expect(validatePhone('12345')).toBe(false);
    });

    it('should reject phone with more than 10 digits', () => {
      expect(validatePhone('12345678901')).toBe(false);
    });

    it('should reject phone with non-numeric characters', () => {
      expect(validatePhone('98765abc10')).toBe(false);
      expect(validatePhone('9876-543210')).toBe(false);
    });
  });

  describe('validateEmail', () => {
    it('should accept valid email addresses', () => {
      expect(validateEmail('test@example.com')).toBe(true);
      expect(validateEmail('user.name@domain.co.in')).toBe(true);
    });

    it('should reject email without @ symbol', () => {
      expect(validateEmail('testexample.com')).toBe(false);
    });

    it('should reject email without domain', () => {
      expect(validateEmail('test@')).toBe(false);
    });

    it('should reject email with spaces', () => {
      expect(validateEmail('test @example.com')).toBe(false);
    });
  });

  describe('validateOTP', () => {
    it('should accept valid 6-digit OTP', () => {
      expect(validateOTP('123456')).toBe(true);
      expect(validateOTP('000000')).toBe(true);
    });

    it('should reject OTP with less than 6 digits', () => {
      expect(validateOTP('12345')).toBe(false);
    });

    it('should reject OTP with more than 6 digits', () => {
      expect(validateOTP('1234567')).toBe(false);
    });

    it('should reject OTP with non-numeric characters', () => {
      expect(validateOTP('12a456')).toBe(false);
    });
  });

  describe('validateRequired', () => {
    it('should accept non-empty strings', () => {
      expect(validateRequired('test')).toBe(true);
      expect(validateRequired('   value   ')).toBe(true);
    });

    it('should reject empty strings', () => {
      expect(validateRequired('')).toBe(false);
      expect(validateRequired('   ')).toBe(false);
    });
  });

  describe('validateKeralaDistrict', () => {
    it('should accept valid Kerala districts', () => {
      expect(validateKeralaDistrict('Thiruvananthapuram')).toBe(true);
      expect(validateKeralaDistrict('Ernakulam')).toBe(true);
      expect(validateKeralaDistrict('Kozhikode')).toBe(true);
    });

    it('should reject invalid district names', () => {
      expect(validateKeralaDistrict('Mumbai')).toBe(false);
      expect(validateKeralaDistrict('Delhi')).toBe(false);
    });

    it('should be case-sensitive', () => {
      expect(validateKeralaDistrict('ernakulam')).toBe(false);
      expect(validateKeralaDistrict('ERNAKULAM')).toBe(false);
    });
  });
});
