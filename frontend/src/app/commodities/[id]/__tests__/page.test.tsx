import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CommodityDetailPage from '../page'

// ---------- Mocks ----------

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn(), replace: vi.fn(), refresh: vi.fn(), prefetch: vi.fn(), forward: vi.fn() }),
  usePathname: () => '/commodities/test-commodity-id',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: 'test-commodity-id' }),
}))

vi.mock('@/components/layout/AppLayout', () => ({
  AppLayout: ({ children }: any) => <div data-testid="app-layout">{children}</div>,
}))

// Mock recharts - render simple divs
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
}))

const mockGetDetails = vi.fn()

vi.mock('@/services/commodities', () => ({
  commoditiesService: {
    getDetails: (...args: any[]) => mockGetDetails(...args),
  },
}))

// ---------- Mock Data ----------

const mockDetail = {
  id: 'test-commodity-id',
  name: 'Rice (Paddy)',
  name_local: 'Dhanya',
  category: 'Cereals',
  unit: 'Quintal',
  description: 'Staple grain',
  current_price: 2500,
  price_changes: {
    '1d': 2.5,
    '7d': -1.2,
    '30d': 5.0,
    '90d': 8.3,
  },
  seasonal_info: {
    is_in_season: true,
    growing_months: [6, 7, 8, 9],
    harvest_months: [10, 11, 12],
  },
  major_producing_states: ['Punjab', 'Haryana'],
  price_history: [
    { date: '2026-01-10', price: 2400 },
    { date: '2026-01-11', price: 2450 },
    { date: '2026-01-12', price: 2480 },
    { date: '2026-01-13', price: 2500 },
  ],
  top_mandis: [
    { name: 'Thrissur Market', district: 'Thrissur', state: 'Kerala', price: 2600, as_of: '2026-01-15' },
    { name: 'Ernakulam Market', district: 'Ernakulam', state: 'Kerala', price: 2550, as_of: '2026-01-15' },
  ],
  bottom_mandis: [
    { name: 'Small Market', district: 'Palakkad', state: 'Kerala', price: 2200, as_of: '2026-01-15' },
  ],
}

// ---------- Tests ----------

describe('CommodityDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetDetails.mockResolvedValue(mockDetail)
  })

  // ========================
  // LOADING STATE
  // ========================
  describe('Loading State', () => {
    it('shows loading text while fetching', () => {
      mockGetDetails.mockImplementation(() => new Promise(() => {}))
      render(<CommodityDetailPage />)
      expect(screen.getByText('Loading commodity details...')).toBeInTheDocument()
    })

    it('renders within AppLayout during loading', () => {
      mockGetDetails.mockImplementation(() => new Promise(() => {}))
      render(<CommodityDetailPage />)
      expect(screen.getByTestId('app-layout')).toBeInTheDocument()
    })
  })

  // ========================
  // ERROR STATE
  // ========================
  describe('Error State', () => {
    it('shows error message on API failure', async () => {
      mockGetDetails.mockRejectedValue(new Error('API error'))
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Failed to load commodity details.')).toBeInTheDocument()
      })
    })

    it('renders within AppLayout on error', async () => {
      mockGetDetails.mockRejectedValue(new Error('err'))
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByTestId('app-layout')).toBeInTheDocument()
      })
    })
  })

  // ========================
  // HEADER
  // ========================
  describe('Header', () => {
    it('displays commodity name', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Rice (Paddy)')).toBeInTheDocument()
      })
    })

    it('displays local name', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Dhanya')).toBeInTheDocument()
      })
    })

    it('shows Back button', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Back')).toBeInTheDocument()
      })
    })

    it('renders within AppLayout', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByTestId('app-layout')).toBeInTheDocument()
      })
    })
  })

  // ========================
  // CURRENT PRICE CARD
  // ========================
  describe('Current Price Card', () => {
    it('displays Current Price title', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Current Price')).toBeInTheDocument()
      })
    })

    it('displays price description', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Average across all mandis')).toBeInTheDocument()
      })
    })

    it('displays current price value', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        const matches = screen.getAllByText('₹2,500')
        expect(matches.length).toBeGreaterThanOrEqual(1)
      })
    })

    it('displays 1d price change percentage', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('2.5%')).toBeInTheDocument()
      })
    })
  })

  // ========================
  // SEASONALITY CARD
  // ========================
  describe('Seasonality Card', () => {
    it('displays Seasonality title', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Seasonality')).toBeInTheDocument()
      })
    })

    it('displays growing months', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText(/Growing:.*Jun, Jul, Aug, Sep/)).toBeInTheDocument()
      })
    })

    it('displays harvest months', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText(/Harvest:.*Oct, Nov, Dec/)).toBeInTheDocument()
      })
    })

    it('shows In Season badge when in season', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('In Season')).toBeInTheDocument()
      })
    })

    it('shows seasonality not available when no data', async () => {
      mockGetDetails.mockResolvedValue({
        ...mockDetail,
        seasonal_info: { is_in_season: false },
      })
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Seasonality data not available for this commodity')).toBeInTheDocument()
      })
    })
  })

  // ========================
  // UNIT CARD
  // ========================
  describe('Unit Card', () => {
    it('displays Unit title', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Unit')).toBeInTheDocument()
      })
    })

    it('displays unit value', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Quintal')).toBeInTheDocument()
      })
    })

    it('displays Trading unit description', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Trading unit')).toBeInTheDocument()
      })
    })
  })

  // ========================
  // PRICE CHART
  // ========================
  describe('Price Chart', () => {
    it('displays chart title', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Historical Prices & Trends')).toBeInTheDocument()
      })
    })

    it('displays chart description with data point count', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText(/Last 4 data points/)).toBeInTheDocument()
      })
    })

    it('renders chart container', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
      })
    })

    it('shows no data message when price_history is empty', async () => {
      mockGetDetails.mockResolvedValue({
        ...mockDetail,
        price_history: [],
      })
      render(<CommodityDetailPage />)
      await waitFor(() => {
        const matches = screen.getAllByText('No historical data available.')
        expect(matches.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  // ========================
  // TOP MANDIS
  // ========================
  describe('Top Mandis', () => {
    it('displays Top Mandis title', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Top Mandis')).toBeInTheDocument()
      })
    })

    it('displays Best prices currently description', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Best prices currently')).toBeInTheDocument()
      })
    })

    it('displays mandi names', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Thrissur Market')).toBeInTheDocument()
        expect(screen.getByText('Ernakulam Market')).toBeInTheDocument()
      })
    })

    it('displays mandi districts', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Thrissur')).toBeInTheDocument()
        expect(screen.getByText('Ernakulam')).toBeInTheDocument()
      })
    })

    it('displays mandi prices', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('₹2,600')).toBeInTheDocument()
        expect(screen.getByText('₹2,550')).toBeInTheDocument()
      })
    })

    it('shows no mandi data message when empty', async () => {
      mockGetDetails.mockResolvedValue({
        ...mockDetail,
        top_mandis: [],
      })
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('No mandi data available.')).toBeInTheDocument()
      })
    })
  })

  // ========================
  // RECENT HISTORY
  // ========================
  describe('Recent History', () => {
    it('displays Recent History title', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Recent History')).toBeInTheDocument()
      })
    })

    it('displays history description', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Daily average prices (all mandis)')).toBeInTheDocument()
      })
    })

    it('displays price history entries', async () => {
      render(<CommodityDetailPage />)
      await waitFor(() => {
        // Prices from history - may appear in multiple places (current price card + history)
        const matches = screen.getAllByText('₹2,500')
        expect(matches.length).toBeGreaterThanOrEqual(1)
      })
    })

    it('shows no data message when history is empty', async () => {
      mockGetDetails.mockResolvedValue({
        ...mockDetail,
        price_history: [],
      })
      render(<CommodityDetailPage />)
      await waitFor(() => {
        const matches = screen.getAllByText('No historical data available.')
        expect(matches.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  // ========================
  // EDGE CASES
  // ========================
  describe('Edge Cases', () => {
    it('handles null current_price gracefully', async () => {
      mockGetDetails.mockResolvedValue({
        ...mockDetail,
        current_price: null,
      })
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('₹N/A')).toBeInTheDocument()
      })
    })

    it('handles null unit gracefully', async () => {
      mockGetDetails.mockResolvedValue({
        ...mockDetail,
        unit: null,
      })
      render(<CommodityDetailPage />)
      await waitFor(() => {
        // Unit card should show N/A
        expect(screen.getByText('N/A')).toBeInTheDocument()
      })
    })

    it('handles no local name', async () => {
      mockGetDetails.mockResolvedValue({
        ...mockDetail,
        name_local: null,
      })
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('Rice (Paddy)')).toBeInTheDocument()
        expect(screen.queryByText('Dhanya')).not.toBeInTheDocument()
      })
    })

    it('handles negative price change', async () => {
      mockGetDetails.mockResolvedValue({
        ...mockDetail,
        price_changes: { '1d': -3.5 },
      })
      render(<CommodityDetailPage />)
      await waitFor(() => {
        expect(screen.getByText('-3.5%')).toBeInTheDocument()
      })
    })
  })
})
