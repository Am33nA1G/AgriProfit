import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Checkbox } from '../checkbox';

describe('Checkbox Component', () => {
  it('renders unchecked by default', () => {
    render(<Checkbox />);
    
    const checkbox = screen.getByRole('checkbox');
    // When checked prop is not provided, aria-checked is undefined (not rendered)
    expect(checkbox).not.toHaveAttribute('aria-checked');
    // Check icon should not be present
    expect(checkbox.querySelector('svg')).not.toBeInTheDocument();
  });

  it('renders checked state', () => {
    render(<Checkbox checked={true} />);
    
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toHaveAttribute('aria-checked', 'true');
    
    // Check icon should be present
    const checkIcon = checkbox.querySelector('svg');
    expect(checkIcon).toBeInTheDocument();
  });

  it('calls onCheckedChange when clicked', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    
    render(<Checkbox checked={false} onCheckedChange={handleChange} />);
    
    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);
    
    expect(handleChange).toHaveBeenCalledWith(true);
  });

  it('toggles from checked to unchecked', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    
    render(<Checkbox checked={true} onCheckedChange={handleChange} />);
    
    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);
    
    expect(handleChange).toHaveBeenCalledWith(false);
  });

  it('renders disabled state', () => {
    render(<Checkbox disabled />);
    
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeDisabled();
  });

  it('does not call onCheckedChange when disabled and clicked', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    
    render(<Checkbox disabled onCheckedChange={handleChange} />);
    
    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);
    
    expect(handleChange).not.toHaveBeenCalled();
  });

  it('applies custom className', () => {
    render(<Checkbox className="custom-checkbox" />);
    
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toHaveClass('custom-checkbox');
  });

  it('shows check icon when checked', () => {
    const { container } = render(<Checkbox checked={true} />);
    
    const checkIcon = container.querySelector('svg');
    expect(checkIcon).toBeInTheDocument();
  });

  it('hides check icon when unchecked', () => {
    const { container } = render(<Checkbox checked={false} />);
    
    const checkIcon = container.querySelector('svg');
    expect(checkIcon).not.toBeInTheDocument();
  });

  it('handles multiple checkboxes independently', async () => {
    const handleChange1 = vi.fn();
    const handleChange2 = vi.fn();
    const user = userEvent.setup();
    
    render(
      <div>
        <Checkbox checked={false} onCheckedChange={handleChange1} />
        <Checkbox checked={true} onCheckedChange={handleChange2} />
      </div>
    );
    
    const checkboxes = screen.getAllByRole('checkbox');
    
    await user.click(checkboxes[0]);
    expect(handleChange1).toHaveBeenCalledWith(true);
    expect(handleChange2).not.toHaveBeenCalled();
  });
});
