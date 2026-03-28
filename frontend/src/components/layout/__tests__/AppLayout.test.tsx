import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppLayout } from '../AppLayout';

// Mock the child components
vi.mock('../Sidebar', () => ({
  Sidebar: () => <div data-testid="sidebar">Sidebar</div>,
}));

vi.mock('../Navbar', () => ({
  Navbar: () => <nav data-testid="navbar">Navbar</nav>,
}));

describe('AppLayout Component', () => {
  it('should render children content', () => {
    render(
      <AppLayout>
        <div>Test content</div>
      </AppLayout>
    );
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('should render Sidebar component', () => {
    render(
      <AppLayout>
        <div>Content</div>
      </AppLayout>
    );
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('should render Navbar component', () => {
    render(
      <AppLayout>
        <div>Content</div>
      </AppLayout>
    );
    expect(screen.getByTestId('navbar')).toBeInTheDocument();
  });

  it('should have proper layout structure', () => {
    const { container } = render(
      <AppLayout>
        <div>Content</div>
      </AppLayout>
    );
    
    const mainLayout = container.querySelector('.flex.min-h-screen');
    expect(mainLayout).toBeInTheDocument();
    expect(mainLayout).toHaveClass('bg-gray-50');
  });

  it('should render main content area', () => {
    const { container } = render(
      <AppLayout>
        <div>Main content</div>
      </AppLayout>
    );
    
    const main = container.querySelector('main');
    expect(main).toBeInTheDocument();
    expect(main).toHaveClass('flex-1', 'overflow-auto');
  });

  it('should render multiple children', () => {
    render(
      <AppLayout>
        <div>First child</div>
        <div>Second child</div>
      </AppLayout>
    );
    
    expect(screen.getByText('First child')).toBeInTheDocument();
    expect(screen.getByText('Second child')).toBeInTheDocument();
  });

  it('should apply dark mode classes', () => {
    const { container } = render(
      <AppLayout>
        <div>Content</div>
      </AppLayout>
    );
    
    const mainLayout = container.querySelector('.flex.min-h-screen');
    expect(mainLayout).toHaveClass('dark:bg-black');
  });
});
