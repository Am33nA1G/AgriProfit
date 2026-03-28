import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../card';

describe('Card Component', () => {
  it('should render card with children', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('should render with CardHeader and CardTitle', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Title</CardTitle>
        </CardHeader>
      </Card>
    );
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('should render with CardDescription', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Test description</CardDescription>
        </CardHeader>
      </Card>
    );
    expect(screen.getByText('Test description')).toBeInTheDocument();
  });

  it('should render with CardContent', () => {
    render(
      <Card>
        <CardContent>Content text</CardContent>
      </Card>
    );
    expect(screen.getByText('Content text')).toBeInTheDocument();
  });

  it('should accept custom className', () => {
    const { container } = render(<Card className="custom-card">Test</Card>);
    const card = container.querySelector('[data-slot="card"]');
    expect(card).toHaveClass('custom-card');
  });

  it('should render complete card structure', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Product Title</CardTitle>
          <CardDescription>Product description</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Main content area</p>
        </CardContent>
      </Card>
    );

    expect(screen.getByText('Product Title')).toBeInTheDocument();
    expect(screen.getByText('Product description')).toBeInTheDocument();
    expect(screen.getByText('Main content area')).toBeInTheDocument();
  });
});
