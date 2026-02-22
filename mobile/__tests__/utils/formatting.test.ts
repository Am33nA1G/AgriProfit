import { formatPrice, formatDate, formatRelativeTime } from '../../src/utils/formatting';
import { validatePhoneNumber, validateOTP } from '../../src/utils/validation';

describe('formatPrice', () => {
  it('formats zero', () => {
    const result = formatPrice(0);
    expect(result).toContain('0');
  });

  it('formats 1500.50 with INR symbol', () => {
    const result = formatPrice(1500.50);
    expect(result).toContain('₹');
    expect(result).toMatch(/1[,.]?500/);
  });

  it('formats 100000 with Indian number formatting', () => {
    const result = formatPrice(100000);
    expect(result).toContain('₹');
    // Should have commas in Indian style: 1,00,000
    expect(result.replace(/[₹\s]/g, '')).toMatch(/1[,.]?00[,.]?000/);
  });

  it('formats negative amounts', () => {
    const result = formatPrice(-500);
    expect(result).toContain('500');
  });
});

describe('formatDate', () => {
  it('formats ISO date string to readable format', () => {
    const result = formatDate('2026-01-15T00:00:00Z');
    expect(result).toContain('15');
    expect(result).toContain('Jan');
    expect(result).toContain('2026');
  });

  it('handles different months', () => {
    const result = formatDate('2026-06-30T00:00:00Z');
    expect(result).toContain('Jun');
  });
});

describe('formatRelativeTime', () => {
  it('returns "just now" for very recent timestamps', () => {
    const now = new Date().toISOString();
    const result = formatRelativeTime(now);
    expect(result).toMatch(/just now|0m|1m/i);
  });

  it('returns hours for timestamps within a day', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    const result = formatRelativeTime(twoHoursAgo);
    expect(result).toMatch(/2h|hour/i);
  });

  it('returns days for older timestamps', () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
    const result = formatRelativeTime(threeDaysAgo);
    expect(result).toMatch(/3d|day/i);
  });
});

describe('validatePhoneNumber', () => {
  it('validates correct Indian mobile numbers', () => {
    expect(validatePhoneNumber('9876543210')).toBe(true);
    expect(validatePhoneNumber('8765432109')).toBe(true);
    expect(validatePhoneNumber('7654321098')).toBe(true);
    expect(validatePhoneNumber('6543210987')).toBe(true);
  });

  it('rejects numbers starting with 5 or below', () => {
    expect(validatePhoneNumber('5123456789')).toBe(false);
    expect(validatePhoneNumber('4123456789')).toBe(false);
    expect(validatePhoneNumber('1234567890')).toBe(false);
  });

  it('rejects numbers with wrong length', () => {
    expect(validatePhoneNumber('987654321')).toBe(false);   // 9 digits
    expect(validatePhoneNumber('98765432101')).toBe(false); // 11 digits
    expect(validatePhoneNumber('')).toBe(false);
  });

  it('rejects non-numeric characters', () => {
    expect(validatePhoneNumber('987654321a')).toBe(false);
    expect(validatePhoneNumber('+919876543210')).toBe(false);
  });
});

describe('validateOTP', () => {
  it('validates 6-digit OTP', () => {
    expect(validateOTP('123456')).toBe(true);
    expect(validateOTP('000000')).toBe(true);
    expect(validateOTP('999999')).toBe(true);
  });

  it('rejects wrong length', () => {
    expect(validateOTP('12345')).toBe(false);
    expect(validateOTP('1234567')).toBe(false);
    expect(validateOTP('')).toBe(false);
  });

  it('rejects non-digits', () => {
    expect(validateOTP('12345a')).toBe(false);
    expect(validateOTP('abcdef')).toBe(false);
  });
});
