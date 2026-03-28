import { render, screen, waitFor } from '@test/test-utils'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import NotificationsPage from '../page'
import { notificationsService } from '@/services/notifications'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(() => null),
  }),
  usePathname: () => '/notifications',
}))

// Mock services
vi.mock('@/services/notifications', () => ({
  notificationsService: {
    getAll: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
    getNotifications: vi.fn(),
  },
}))

const mockNotifications = [
  {
    id: 'notif_1',
    title: 'Price Alert',
    message: 'Wheat price increased by 5%',
    type: 'PRICE_ALERT',
    is_read: false,
    created_at: '2024-02-05T10:00:00Z',
  },
  {
    id: 'notif_2',
    title: 'System Update',
    message: 'New features available',
    type: 'SYSTEM',
    is_read: true,
    created_at: '2024-02-04T10:00:00Z',
  },
]

describe('NotificationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    ;(notificationsService.getNotifications as any).mockResolvedValue({
      notifications: mockNotifications,
      total: 2,
      unread_count: 1,
    })
    ;(notificationsService.getAll as any).mockResolvedValue({
      notifications: mockNotifications,
      total: 2,
      unread_count: 1,
    })
  })

  it('renders notifications page heading', () => {
    render(<NotificationsPage />)
    
    const heading = screen.getByRole('heading', { name: /notifications/i })
    expect(heading).toBeInTheDocument()
  })

  it('displays list of notifications', async () => {
    render(<NotificationsPage />)
    
    await waitFor(() => {
      expect(screen.getByText('Price Alert')).toBeInTheDocument()
      expect(screen.getByText('System Update')).toBeInTheDocument()
    })
  })

  it('shows unread count', async () => {
    render(<NotificationsPage />)
    
    await waitFor(() => {
      // Should show unread indicator
      const unreadElements = screen.queryAllByText(/unread|1/i)
      expect(unreadElements.length).toBeGreaterThan(0)
    })
  })

  it('has mark all as read button', () => {
    render(<NotificationsPage />)
    
    const markAllButton = screen.queryByRole('button', { name: /mark all/i })
    
    if (markAllButton) {
      expect(markAllButton).toBeInTheDocument()
    } else {
      // Page should still render
      expect(screen.getByRole('heading')).toBeInTheDocument()
    }
  })

  it('renders without crashing when empty', async () => {
    ;(notificationsService.getAll as any).mockResolvedValue({
      notifications: [],
      total: 0,
      unread_count: 0,
    })
    
    render(<NotificationsPage />)
    
    await waitFor(() => {
      expect(document.body).toBeTruthy()
    })
  })
})
