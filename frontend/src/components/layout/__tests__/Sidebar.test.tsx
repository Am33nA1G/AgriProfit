import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Sidebar } from '../Sidebar';

const mockPush = vi.fn();

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe('Sidebar Component', () => {
  beforeEach(() => {
    localStorage.clear();
    mockPush.mockClear();
  });

  it('should render all main navigation items', () => {
    render(<Sidebar />);
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Commodities')).toBeInTheDocument();
    expect(screen.getByText('Mandis')).toBeInTheDocument();
    expect(screen.getByText('Inventory')).toBeInTheDocument();
    expect(screen.getByText('Sales')).toBeInTheDocument();
    expect(screen.getByText('Transport')).toBeInTheDocument();
    expect(screen.getByText('Market Research')).toBeInTheDocument();
    expect(screen.getByText('Community')).toBeInTheDocument();
    expect(screen.getByText('Notifications')).toBeInTheDocument();
  });

  it('should render AgriProfit logo', () => {
    render(<Sidebar />);
    expect(screen.getByText('AgriProfit')).toBeInTheDocument();
  });

  it('should show Admin link when user is admin', () => {
    localStorage.setItem('user', JSON.stringify({ role: 'admin' }));
    render(<Sidebar />);
    
    const adminLinks = screen.getAllByText('Admin');
    expect(adminLinks.length).toBeGreaterThan(0); // Should find both header and link
  });

  it('should not show Admin link when user is not admin', () => {
    localStorage.setItem('user', JSON.stringify({ role: 'farmer' }));
    render(<Sidebar />);
    
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  });

  it('should handle logout click', async () => {
    const user = userEvent.setup();
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('user', JSON.stringify({ role: 'farmer' }));
    
    render(<Sidebar />);
    
    const logoutButton = screen.getByRole('button', { name: /logout/i });
    await user.click(logoutButton);
    
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(mockPush).toHaveBeenCalledWith('/login');
  });

  it('should highlight active navigation item', () => {
    const { container } = render(<Sidebar />);
    
    // Find the Dashboard link (should be active since pathname is /dashboard)
    const dashboardLink = screen.getByText('Dashboard').closest('a');
    expect(dashboardLink).toHaveClass('bg-green-100');
  });

  it('should render Main Menu section header', () => {
    render(<Sidebar />);
    expect(screen.getByText('Main Menu')).toBeInTheDocument();
  });

  it('should render Admin section header when user is admin', () => {
    localStorage.setItem('user', JSON.stringify({ role: 'admin' }));
    render(<Sidebar />);
    
    // Verify admin section exists by checking for admin link
    const adminLink = screen.getByRole('link', { name: /admin/i });
    expect(adminLink).toBeInTheDocument();
    expect(adminLink).toHaveAttribute('href', '/admin');
  });

  it('should have proper sidebar structure', () => {
    const { container } = render(<Sidebar />);
    
    const sidebar = container.querySelector('aside');
    expect(sidebar).toBeInTheDocument();
    expect(sidebar).toHaveClass('hidden', 'lg:flex', 'w-64');
  });
});
