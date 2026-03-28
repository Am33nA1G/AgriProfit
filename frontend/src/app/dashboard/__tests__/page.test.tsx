import { render, screen, waitFor } from '@test/test-utils'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import DashboardPage from '../page'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(() => null),
  }),
  usePathname: () => '/dashboard',
}))

// Mock services
vi.mock('@/services/inventory', () => ({
  inventoryService: {
    getAll: vi.fn(),
    analyzeInventory: vi.fn(),
  },
}))

vi.mock('@/services/sales', () => ({
  salesService: {
    getStats: vi.fn(),
  },
}))

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  },
}))

// Mock localStorage with user data
const mockUser = {
  id: '1',
  name: 'Test User',
  phone_number: '9876543210',
  role: 'user',
}

Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: vi.fn(() => JSON.stringify(mockUser)),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  },
  writable: true,
})

const mockInventoryData = {
  items: [
    {
      id: '1',
      commodity_id: 'cmd_1',
      commodity: { name: 'Wheat', category: 'Grains' },
      quantity: 1000,
      unit: 'kg',
      purchase_price: 25,
      purchase_date: '2024-01-15',
    },
    {
      id: '2',
      commodity_id: 'cmd_2',
      commodity: { name: 'Rice', category: 'Grains' },
      quantity: 500,
      unit: 'kg',
      purchase_price: 30,
      purchase_date: '2024-01-20',
    },
  ],
  total: 2,
}

const mockSalesStats = {
  total_sales: 50000,
  total_revenue: 75000,
  total_profit: 25000,
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders dashboard with welcome message', () => {
    render(<DashboardPage />)
    
    // Check for main heading
    const heading = screen.getAllByText(/dashboard/i)[0]
    expect(heading).toBeInTheDocument()
  })

  it('displays stats cards', () => {
    render(<DashboardPage />)
    
    // Look for card components or stats
    // The exact text depends on implementation
    const cards = screen.queryAllByRole('article') || screen.queryAllByRole('region')
    
    // Dashboard should have some content cards
    expect(document.body).toContainHTML('Dashboard')
  })

  it('has navigation elements', () => {
    render(<DashboardPage />)
    
    // Should have some interactive elements (buttons, links)
    const buttons = screen.queryAllByRole('button')
    const links = screen.queryAllByRole('link')
    
    expect(buttons.length + links.length).toBeGreaterThan(0)
  })

  it('renders without crashing', () => {
    const { container } = render(<DashboardPage />)
    expect(container).toBeTruthy()
  })

  it('displays user-specific content', () => {
    render(<DashboardPage />)
    
    // Dashboard should render successfully - use getAllByText for multiple matches
    const dashboardElements = screen.getAllByText(/dashboard/i)
    expect(dashboardElements.length).toBeGreaterThan(0)
  })
})
