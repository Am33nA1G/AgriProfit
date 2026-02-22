import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import OTPInput from '../../../src/components/forms/OTPInput';

describe('OTPInput', () => {
  it('renders 6 input boxes', () => {
    const onChange = jest.fn();
    const { getAllByTestId } = render(<OTPInput length={6} onChange={onChange} />);
    // Note: test IDs are on individual TextInput elements
    const inputs = getAllByTestId(/otp-input-/);
    expect(inputs).toHaveLength(6);
  });

  it('calls onChange with complete 6-digit code', () => {
    const onChange = jest.fn();
    const { getAllByTestId } = render(<OTPInput length={6} onChange={onChange} />);
    const inputs = getAllByTestId(/otp-input-/);

    // Enter digits one by one
    '123456'.split('').forEach((digit, i) => {
      fireEvent.changeText(inputs[i], digit);
    });

    expect(onChange).toHaveBeenCalledWith('123456');
  });

  it('calls onChange with partial code as user types', () => {
    const onChange = jest.fn();
    const { getAllByTestId } = render(<OTPInput length={6} onChange={onChange} />);
    const inputs = getAllByTestId(/otp-input-/);

    fireEvent.changeText(inputs[0], '1');
    expect(onChange).toHaveBeenCalledWith('1');
  });

  it('accepts value prop to display pre-filled code', () => {
    const onChange = jest.fn();
    const { getAllByTestId } = render(
      <OTPInput length={6} onChange={onChange} value="123456" />,
    );
    const inputs = getAllByTestId(/otp-input-/);
    expect(inputs[0].props.value).toBe('1');
    expect(inputs[5].props.value).toBe('6');
  });
});
