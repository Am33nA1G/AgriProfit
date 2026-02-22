import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import LoginScreen from '../../../src/screens/auth/LoginScreen';

// Mock navigation
const mockNavigate = jest.fn();
jest.mock('@react-navigation/native-stack', () => ({
  NativeStackScreenProps: {},
}));

const mockNavigation = {
  navigate: mockNavigate,
  goBack: jest.fn(),
  replace: jest.fn(),
} as any;

const mockRoute = { key: 'Login', name: 'Login' } as any;

// Mock auth API
jest.mock('../../../src/api/auth', () => ({
  authApi: {
    requestOTP: jest.fn().mockResolvedValue({ data: { message: 'OTP sent' } }),
  },
}));

describe('LoginScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders phone number input', () => {
    const { getByPlaceholderText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />,
    );
    expect(getByPlaceholderText(/9876543210/i)).toBeTruthy();
  });

  it('renders send OTP button', () => {
    const { getByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />,
    );
    expect(getByText(/send otp/i)).toBeTruthy();
  });

  it('shows validation error for invalid phone number', async () => {
    const { getByPlaceholderText, getByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />,
    );

    const input = getByPlaceholderText(/9876543210/i);
    fireEvent.changeText(input, '12345');

    const button = getByText(/send otp/i);
    fireEvent.press(button);

    await waitFor(() => {
      expect(getByText(/valid/i)).toBeTruthy();
    });
  });

  it('shows validation error for number starting with invalid digit', async () => {
    const { getByPlaceholderText, getByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />,
    );

    const input = getByPlaceholderText(/9876543210/i);
    fireEvent.changeText(input, '5123456789');

    fireEvent.press(getByText(/send otp/i));

    await waitFor(() => {
      expect(getByText(/valid/i)).toBeTruthy();
    });
  });

  it('navigates to OTP screen for valid phone number', async () => {
    const { authApi } = require('../../../src/api/auth');
    const { getByPlaceholderText, getByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />,
    );

    const input = getByPlaceholderText(/9876543210/i);
    fireEvent.changeText(input, '9876543210');

    fireEvent.press(getByText(/send otp/i));

    await waitFor(() => {
      expect(authApi.requestOTP).toHaveBeenCalledWith('9876543210');
      expect(mockNavigate).toHaveBeenCalledWith('OTP', expect.objectContaining({
        phoneNumber: '9876543210',
      }));
    });
  });
});
