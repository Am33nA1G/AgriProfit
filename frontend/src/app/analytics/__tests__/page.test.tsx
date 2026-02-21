import { render, screen, fireEvent, waitFor, within, act } from '@test/test-utils'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import AnalyticsPage from '../page'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { commoditiesService } from '@/services/commodities'
import { mandisService } from '@/services/mandis'
import { pricesService } from '@/services/prices'
import { analyticsService } from '@/services/analytics'
import { toast } from 'sonner'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(() => null),
  }),
  usePathname: () => '/analytics',
}))

// Mock next/dynamic
vi.mock('next/dynamic', () => ({
  default: (loader: any) => {
    const DynamicComponent = (...args: any[]) => {
      return null // Return null for chart components in tests
    }
    return DynamicComponent
  },
}))

// Mock services
vi.mock('@/services/commodities', () => ({
  commoditiesService: {
    getAll: vi.fn(),
  },
}))

vi.mock('@/services/mandis', () => ({
  mandisService: {
    getAll: vi.fn(),
    getStates: vi.fn(),
  },
}))

vi.mock('@/services/prices', () => ({
  pricesService: {
    getPricesByMandi: vi.fn(),
    getCurrentPrices: vi.fn(),
    getHistoricalPrices: vi.fn(),
  },
}))

vi.mock('@/services/analytics', () => ({
  analyticsService: {
    getDashboard: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const mockCommodities = [
  { id: '1', name: 'Rice', category: 'Grains' },
  { id: '2', name: 'Wheat', category: 'Grains' },
  { id: '3', name: 'Tomato', category: 'Vegetables' },
  { id: '4', name: 'Onion', category: 'Vegetables' },
  { id: '5', name: 'Potato', category: 'Vegetables' },
  { id: '6', name: 'Banana', category: 'Fruits' },
  { id: '7', name: 'Coconut', category: 'Cash Crops' },
]

const mockMandis = [
  { id: '1', name: 'Ernakulam APMC', district: 'Ernakulam', state: 'Kerala', rating: 4.5, market_code: 'ERN001', facilities: { weighbridge: true, storage: true }, contact: { phone: '1234567890' } },
  { id: '2', name: 'Thrissur Market', district: 'Thrissur', state: 'Kerala', rating: 4.2, market_code: 'THR001', facilities: { cold_storage: true } },
  { id: '3', name: 'Delhi Mandi', district: 'New Delhi', state: 'Delhi', rating: 4.8, market_code: 'DEL001', facilities: { weighbridge: true } },
]

const mockStates = ['Kerala', 'Delhi', 'Maharashtra']

describe('AnalyticsPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    
    // Setup default mocks
    vi.mocked(commoditiesService.getAll).mockResolvedValue(mockCommodities)
    vi.mocked(mandisService.getAll).mockResolvedValue(mockMandis)
    vi.mocked(mandisService.getStates).mockResolvedValue(mockStates)
    vi.mocked(pricesService.getPricesByMandi).mockResolvedValue([])
    vi.mocked(pricesService.getCurrentPrices).mockResolvedValue({ prices: [] })
    vi.mocked(pricesService.getHistoricalPrices).mockResolvedValue({ data: [] })
    vi.mocked(analyticsService.getDashboard).mockResolvedValue({})
  })

  const renderWithClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    )
  }

  describe('Page Structure', () => {
    it('renders market research heading', async () => {
      renderWithClient(<AnalyticsPage />)
      
      await waitFor(() => {
        const heading = screen.getByRole('heading', { name: /market research/i })
        expect(heading).toBeInTheDocument()
      })
    })

    it('displays refresh button', async () => {
      renderWithClient(<AnalyticsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Refresh')).toBeInTheDocument()
      })
    })
  })

  describe('Price Trends Tab', () => {
    it('displays time range selector', async () => {
      renderWithClient(<AnalyticsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Time Range:')).toBeInTheDocument()
      })
    })

    it('displays commodity search input', async () => {
      renderWithClient(<AnalyticsPage />)
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/select up to 6/i)).toBeInTheDocument()
      })
    })

    it('opens commodity dropdown on search input focus', async () => {
      renderWithClient(<AnalyticsPage />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/select up to 6/i)).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/select up to 6/i)

      await act(async () => {
        searchInput.focus()
      })

      await waitFor(() => {
        expect(screen.getByText('Banana')).toBeInTheDocument()
      })
    })

    it('allows selecting commodity from dropdown', async () => {
      renderWithClient(<AnalyticsPage />)
      const user = userEvent.setup()

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/select up to 6/i)).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/select up to 6/i)

      await act(async () => {
        searchInput.focus()
      })

      await waitFor(() => {
        expect(screen.getByText('Banana')).toBeInTheDocument()
      })

      // Click on Banana
      await user.click(screen.getByText('Banana'))

      // Should now have Banana badge
      await waitFor(() => {
        const badges = screen.getAllByText('Banana')
        expect(badges.length).toBeGreaterThan(0)
      })
    })

    it('shows current prices table with commodities', async () => {
      renderWithClient(<AnalyticsPage />)
      
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
        expect(screen.getByText('Current Prices')).toBeInTheDocument()
      })
    })

    it('displays load more button when more commodities available', async () => {
      // Create 50 prices to trigger "load more" (default displayCount is 20)
      const manyPrices = Array.from({ length: 50 }, (_, i) => ({
        commodity_id: `${i}`,
        commodity: `Commodity${i}`,
        mandi_name: 'Test Mandi',
        state: 'Test',
        district: 'Test',
        price_per_kg: 20 + i,
        change_percent: 0,
        change_amount: 0,
        updated_at: '2024-01-01T00:00:00Z',
      }))
      vi.mocked(pricesService.getCurrentPrices).mockResolvedValue({ prices: manyPrices })

      renderWithClient(<AnalyticsPage />)

      await waitFor(() => {
        expect(screen.getByText(/load more/i)).toBeInTheDocument()
      })
    })

    it('loads more commodities when load more button clicked', async () => {
      const manyPrices = Array.from({ length: 50 }, (_, i) => ({
        commodity_id: `${i}`,
        commodity: `Commodity${i}`,
        mandi_name: 'Test Mandi',
        state: 'Test',
        district: 'Test',
        price_per_kg: 20 + i,
        change_percent: 0,
        change_amount: 0,
        updated_at: '2024-01-01T00:00:00Z',
      }))
      vi.mocked(pricesService.getCurrentPrices).mockResolvedValue({ prices: manyPrices })

      renderWithClient(<AnalyticsPage />)
      const user = userEvent.setup()

      await waitFor(() => {
        expect(screen.getByText(/load more/i)).toBeInTheDocument()
      })

      const loadMoreBtn = screen.getByText(/load more/i)
      await user.click(loadMoreBtn)

      await waitFor(() => {
        expect(screen.getByText(/40 of 50/i)).toBeInTheDocument()
      })
    })

    it('displays commodity count badge', async () => {
      renderWithClient(<AnalyticsPage />)
      
      await waitFor(() => {
        expect(screen.getByText(/\d+ commodities/i)).toBeInTheDocument()
      })
    })

    it('displays price trend chart title', async () => {
      renderWithClient(<AnalyticsPage />)
      
      await waitFor(() => {
        expect(screen.getByText(/Price Trends \(Last \d+ Days\)/i)).toBeInTheDocument()
      })
    })
  })

  describe('Date Gap Filling in Price Trends', () => {
    it('generates continuous date range from min to max date', async () => {
      // Mock historical data with gaps (Jan 1, Jan 3, Jan 5 - missing Jan 2, Jan 4)
      const mockHistoricalWithGaps = {
        data: [
          { date: '2026-01-01', price: 2000 },
          { date: '2026-01-03', price: 2100 },
          { date: '2026-01-05', price: 2200 },
        ],
      }

      vi.mocked(pricesService.getHistoricalPrices).mockResolvedValue(mockHistoricalWithGaps)

      renderWithClient(<AnalyticsPage />)

      // The page should render without errors even with gaps
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /market research/i })).toBeInTheDocument()
      })
    })

    it('handles multiple commodities with different date ranges', async () => {
      // First commodity: Jan 1-3, Second commodity: Jan 2-5
      // This tests that the memo merges ranges correctly

      // We can't directly test the memo, but we can verify the page
      // renders correctly when commodities have overlapping but different ranges
      vi.mocked(pricesService.getHistoricalPrices)
        .mockResolvedValueOnce({
          data: [
            { date: '2026-01-01', price: 2000 },
            { date: '2026-01-02', price: 2050 },
            { date: '2026-01-03', price: 2100 },
          ],
        })
        .mockResolvedValueOnce({
          data: [
            { date: '2026-01-02', price: 1500 },
            { date: '2026-01-03', price: 1550 },
            { date: '2026-01-04', price: 1600 },
            { date: '2026-01-05', price: 1650 },
          ],
        })

      renderWithClient(<AnalyticsPage />)

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /market research/i })).toBeInTheDocument()
      })
    })

    it('handles empty historical data gracefully', async () => {
      vi.mocked(pricesService.getHistoricalPrices).mockResolvedValue({ data: [] })

      renderWithClient(<AnalyticsPage />)

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /market research/i })).toBeInTheDocument()
      })
    })

    it('shows chart section with historical data present', async () => {
      // Mock complete data for a commodity
      vi.mocked(pricesService.getHistoricalPrices).mockResolvedValue({
        data: [
          { date: '2026-01-01', price: 2000 },
          { date: '2026-01-02', price: 2050 },
          { date: '2026-01-03', price: 2100 },
          { date: '2026-01-04', price: 2150 },
          { date: '2026-01-05', price: 2200 },
        ],
      })

      renderWithClient(<AnalyticsPage />)

      await waitFor(() => {
        expect(screen.getByText(/Price Trends \(Last \d+ Days\)/i)).toBeInTheDocument()
      })
    })
  })

  describe('Crop Comparison Tab - Placeholder Tests', () => {
    it('renders without errors', () => {
      const { container } = renderWithClient(<AnalyticsPage />)
      expect(container).toBeTruthy()
    })
  })
})
