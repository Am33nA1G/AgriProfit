import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton } from '../skeleton';

describe('Skeleton Component', () => {
  it('renders skeleton element', () => {
    const { container } = render(<Skeleton />);
    
    const skeleton = container.querySelector('.animate-pulse');
    expect(skeleton).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<Skeleton className="custom-skeleton" />);
    
    const skeleton = container.firstChild;
    expect(skeleton).toHaveClass('custom-skeleton');
    expect(skeleton).toHaveClass('animate-pulse');
  });

  it('renders with custom width and height', () => {
    const { container } = render(
      <Skeleton className="w-full h-12" />
    );
    
    const skeleton = container.firstChild;
    expect(skeleton).toHaveClass('w-full', 'h-12');
  });

  it('renders multiple skeletons for loading state', () => {
    render(
      <div>
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-3/4 mb-2" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
    
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(3);
  });

  it('renders circular skeleton', () => {
    const { container } = render(
      <Skeleton className="h-12 w-12 rounded-full" />
    );
    
    const skeleton = container.firstChild;
    expect(skeleton).toHaveClass('rounded-full');
  });

  it('renders rectangular skeleton', () => {
    const { container } = render(
      <Skeleton className="h-32 w-full" />
    );
    
    const skeleton = container.firstChild;
    expect(skeleton).toHaveClass('h-32', 'w-full');
  });
});
