import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../badge';

describe('Badge Component', () => {
  it('renders badge with text', () => {
    render(<Badge>New</Badge>);
    
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('renders default variant', () => {
    render(<Badge>Default</Badge>);
    
    const badge = screen.getByText('Default');
    expect(badge).toHaveAttribute('data-variant', 'default');
  });

  it('renders secondary variant', () => {
    render(<Badge variant="secondary">Secondary</Badge>);
    
    const badge = screen.getByText('Secondary');
    expect(badge).toHaveAttribute('data-variant', 'secondary');
  });

  it('renders destructive variant', () => {
    render(<Badge variant="destructive">Error</Badge>);
    
    const badge = screen.getByText('Error');
    expect(badge).toHaveAttribute('data-variant', 'destructive');
  });

  it('renders outline variant', () => {
    render(<Badge variant="outline">Outline</Badge>);
    
    const badge = screen.getByText('Outline');
    expect(badge).toHaveAttribute('data-variant', 'outline');
  });

  it('renders ghost variant', () => {
    render(<Badge variant="ghost">Ghost</Badge>);
    
    const badge = screen.getByText('Ghost');
    expect(badge).toHaveAttribute('data-variant', 'ghost');
  });

  it('renders link variant', () => {
    render(<Badge variant="link">Link</Badge>);
    
    const badge = screen.getByText('Link');
    expect(badge).toHaveAttribute('data-variant', 'link');
  });

  it('accepts custom className', () => {
    render(<Badge className="custom-badge">Custom</Badge>);
    
    const badge = screen.getByText('Custom');
    expect(badge).toHaveClass('custom-badge');
  });

  it('renders with icon', () => {
    render(
      <Badge>
        <svg data-testid="badge-icon" />
        With Icon
      </Badge>
    );
    
    expect(screen.getByTestId('badge-icon')).toBeInTheDocument();
    expect(screen.getByText('With Icon')).toBeInTheDocument();
  });

  it('renders as different element with asChild', () => {
    render(
      <Badge asChild>
        <a href="/test">Link Badge</a>
      </Badge>
    );
    
    const link = screen.getByText('Link Badge');
    expect(link.tagName).toBe('A');
    expect(link).toHaveAttribute('href', '/test');
  });

  it('renders multiple badges', () => {
    render(
      <div>
        <Badge>Badge 1</Badge>
        <Badge variant="secondary">Badge 2</Badge>
        <Badge variant="destructive">Badge 3</Badge>
      </div>
    );
    
    expect(screen.getByText('Badge 1')).toBeInTheDocument();
    expect(screen.getByText('Badge 2')).toBeInTheDocument();
    expect(screen.getByText('Badge 3')).toBeInTheDocument();
  });
});
