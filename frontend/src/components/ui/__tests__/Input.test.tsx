import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { Input } from '../input';

describe('Input Component', () => {
  it('renders input element', () => {
    render(<Input />);
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
  });

  it('renders with placeholder text', () => {
    render(<Input placeholder="Enter your name" />);
    expect(screen.getByPlaceholderText('Enter your name')).toBeInTheDocument();
  });

  it('handles value controlled by parent', async () => {
    const TestComponent = () => {
      const [value, setValue] = React.useState('');
      return <Input value={value} onChange={(e) => setValue(e.target.value)} />;
    };
    
    render(<TestComponent />);
    const user = userEvent.setup();
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Hello');
    
    expect(input).toHaveValue('Hello');
  });

  it('calls onChange handler when typing', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    
    render(<Input onChange={handleChange} />);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'test');
    
    expect(handleChange).toHaveBeenCalled();
    expect(handleChange).toHaveBeenCalledTimes(4); // One call per character
  });

  it('renders disabled state', () => {
    render(<Input disabled />);
    const input = screen.getByRole('textbox');
    
    expect(input).toBeDisabled();
    expect(input).toHaveClass('disabled:opacity-50');
  });

  it('accepts custom className', () => {
    render(<Input className="custom-input" />);
    const input = screen.getByRole('textbox');
    
    expect(input).toHaveClass('custom-input');
  });

  it('supports different input types', () => {
    const { rerender } = render(<Input type="email" />);
    let input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('type', 'email');
    
    rerender(<Input type="password" />);
    input = screen.getByDisplayValue('') as HTMLInputElement;
    expect(input.type).toBe('password');
    
    rerender(<Input type="number" />);
    input = screen.getByRole('spinbutton');
    expect(input).toHaveAttribute('type', 'number');
  });

  it('shows validation state with aria-invalid', () => {
    render(<Input aria-invalid={true} />);
    const input = screen.getByRole('textbox');
    
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveClass('aria-invalid:border-destructive');
  });

  it('accepts default value', () => {
    render(<Input defaultValue="Initial value" />);
    const input = screen.getByRole('textbox');
    
    expect(input).toHaveValue('Initial value');
  });

  it('can be required', () => {
    render(<Input required />);
    const input = screen.getByRole('textbox');
    
    expect(input).toHaveAttribute('required');
  });

  it('supports maxLength attribute', async () => {
    const user = userEvent.setup();
    
    render(<Input maxLength={5} />);
    const input = screen.getByRole('textbox');
    
    await user.type(input, '1234567890');
    
    // Should only allow 5 characters
    expect(input).toHaveValue('12345');
  });

  it('supports pattern validation', () => {
    render(<Input pattern="[0-9]*" />);
    const input = screen.getByRole('textbox');
    
    expect(input).toHaveAttribute('pattern', '[0-9]*');
  });

  it('renders with name attribute', () => {
    render(<Input name="username" />);
    const input = screen.getByRole('textbox');
    
    expect(input).toHaveAttribute('name', 'username');
  });

  it('supports autoComplete attribute', () => {
    render(<Input autoComplete="email" />);
    const input = screen.getByRole('textbox');
    
    expect(input).toHaveAttribute('autoComplete', 'email');
  });

  it('can be auto-focused', () => {
    render(<Input autoFocus />);
    const input = screen.getByRole('textbox');
    
    // autoFocus is a boolean DOM property, not an attribute
    expect(document.activeElement).toBe(input);
  });

  it('renders email input type correctly', () => {
    render(<Input type="email" placeholder="email@example.com" />);
    const input = screen.getByRole('textbox');
    
    expect(input).toHaveAttribute('type', 'email');
    expect(screen.getByPlaceholderText('email@example.com')).toBeInTheDocument();
  });

  it('renders number input with step attribute', () => {
    render(<Input type="number" step="0.01" />);
    const input = screen.getByRole('spinbutton');
    
    expect(input).toHaveAttribute('step', '0.01');
  });

  it('handles readonly state', () => {
    render(<Input readOnly value="Cannot edit" />);
    const input = screen.getByRole('textbox');
    
    expect(input).toHaveAttribute('readOnly');
    expect(input).toHaveValue('Cannot edit');
  });
});
