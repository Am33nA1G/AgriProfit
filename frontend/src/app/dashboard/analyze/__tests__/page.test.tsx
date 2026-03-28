import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import AnalyzeInventoryPage from '../page'

// ---------- Mocks ----------

const mockPush = vi.fn()
const mockBack = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, back: mockBack, replace: vi.fn(), refresh: vi.fn(), prefetch: vi.fn(), forward: vi.fn() }),
  usePathname: () => '/dashboard/analyze',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}))

vi.mock('@/components/layout/AppLayout', () => ({
  AppLayout: ({ children }: any) => <div data-testid="app-layout">{children}</div>,
}))

const mockAnalyzeInventory = vi.fn()

vi.mock('@/services/inventory', () => ({
  inventoryService: {
    analyzeInventory: (...args: any[]) => mockAnalyzeInventory(...args),
  },
}))

// ---------- Mock Data ----------

const mockAnalysis = {
  total_items: 2,
  total_estimated_min_revenue: 45000,
  total_estimated_max_revenue: 65000,
  analysis: [
    {
      commodity_id: 'c1',
      commodity_name: 'Rice',
      quantity: 100,
      unit: 'kg',
      recommended_mandi: 'Thrissur Market',
      recommended_price: 2500,
      estimated_min_revenue: 25000,
      estimated_max_revenue: 35000,
      best_mandis: [
        {
          mandi_id: 'm1',
          mandi_name: 'Thrissur Market',
          state: 'Kerala',
          district: 'Thrissur',
          modal_price: 2500,
          min_price: 2200,
          max_price: 2800,
          price_date: '2026-01-15T10:00:00Z',
          estimated_revenue: 25000,
          estimated_min_revenue: 22000,
          estimated_max_revenue: 28000,
          is_local: true,
        },
        {
          mandi_id: 'm2',
          mandi_name: 'Ernakulam Market',
          state: 'Kerala',
          district: 'Ernakulam',
          modal_price: 2400,
          min_price: 2100,
          max_price: 2700,
          price_date: '2026-01-15T10:00:00Z',
          estimated_revenue: 24000,
          estimated_min_revenue: 21000,
          estimated_max_revenue: 27000,
          is_local: false,
        },
      ],
    },
    {
      commodity_id: 'c2',
      commodity_name: 'Wheat',
      quantity: 50,
      unit: 'kg',
      recommended_mandi: 'Delhi Market',
      recommended_price: 2200,
      estimated_min_revenue: 20000,
      estimated_max_revenue: 30000,
      best_mandis: [
        {
          mandi_id: 'm3',
          mandi_name: 'Delhi Market',
          state: 'Delhi',
          district: 'New Delhi',
          modal_price: 2200,
          min_price: 2000,
          max_price: 2500,
          price_date: '2026-01-14T10:00:00Z',
          estimated_revenue: 22000,
          estimated_min_revenue: 20000,
          estimated_max_revenue: 25000,
          is_local: false,
        },
      ],
    },
  ],
}

// ---------- Tests ----------

describe('AnalyzeInventoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem('token', 'test-token')
    mockAnalyzeInventory.mockResolvedValue(mockAnalysis)
  })

  afterEach(() => {
    localStorage.clear()
  })

  // ========================
  // AUTH CHECK
  // ========================
  describe('Authentication', () => {
    it('redirects to /login when no token', async () => {
      localStorage.removeItem('token')
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login')
      })
    })

    it('does not redirect when token exists', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(mockAnalyzeInventory).toHaveBeenCalled()
      })
      expect(mockPush).not.toHaveBeenCalledWith('/login')
    })
  })

  // ========================
  // LOADING STATE
  // ========================
  describe('Loading State', () => {
    it('shows loading text while fetching', () => {
      mockAnalyzeInventory.mockImplementation(() => new Promise(() => {})) // never resolves
      render(<AnalyzeInventoryPage />)
      expect(screen.getByText('Analyzing your inventory...')).toBeInTheDocument()
    })

    it('shows loading subtitle', () => {
      mockAnalyzeInventory.mockImplementation(() => new Promise(() => {}))
      render(<AnalyzeInventoryPage />)
      expect(screen.getByText('Finding the best prices across mandis')).toBeInTheDocument()
    })
  })

  // ========================
  // HEADER
  // ========================
  describe('Header', () => {
    it('displays page title', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Inventory Analysis')).toBeInTheDocument()
      })
    })

    it('displays page subtitle', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Find the best mandis to sell your crops')).toBeInTheDocument()
      })
    })

    it('has back button', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Inventory Analysis')).toBeInTheDocument()
      })
    })

    it('renders within AppLayout', () => {
      render(<AnalyzeInventoryPage />)
      expect(screen.getByTestId('app-layout')).toBeInTheDocument()
    })
  })

  // ========================
  // ERROR STATE
  // ========================
  describe('Error State', () => {
    it('shows error card when analysis fails', async () => {
      mockAnalyzeInventory.mockRejectedValue({ response: { data: { detail: 'Server error' } } })
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Analysis Failed')).toBeInTheDocument()
      })
    })

    it('shows error message from API', async () => {
      mockAnalyzeInventory.mockRejectedValue({ response: { data: { detail: 'Server error' } } })
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Server error')).toBeInTheDocument()
      })
    })

    it('shows Try Again button on error', async () => {
      mockAnalyzeInventory.mockRejectedValue({ response: { data: { detail: 'Error' } } })
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Try Again')).toBeInTheDocument()
      })
    })

    it('shows generic error when no detail provided', async () => {
      mockAnalyzeInventory.mockRejectedValue(new Error('something'))
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Failed to analyze inventory. Please try again.')).toBeInTheDocument()
      })
    })

    it('redirects on 401 error', async () => {
      mockAnalyzeInventory.mockRejectedValue({ response: { status: 401 } })
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login')
      })
    })

    it('redirects on network error', async () => {
      mockAnalyzeInventory.mockRejectedValue({ message: 'Network Error' })
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login')
      })
    })
  })

  // ========================
  // EMPTY INVENTORY
  // ========================
  describe('Empty Inventory', () => {
    it('shows empty state when total_items is 0', async () => {
      mockAnalyzeInventory.mockResolvedValue({ total_items: 0, analysis: [], total_estimated_min_revenue: 0, total_estimated_max_revenue: 0 })
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('No Inventory Found')).toBeInTheDocument()
      })
    })

    it('shows guidance text for empty inventory', async () => {
      mockAnalyzeInventory.mockResolvedValue({ total_items: 0, analysis: [], total_estimated_min_revenue: 0, total_estimated_max_revenue: 0 })
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText(/Add items to your inventory/)).toBeInTheDocument()
      })
    })

    it('shows Go to Inventory button', async () => {
      mockAnalyzeInventory.mockResolvedValue({ total_items: 0, analysis: [], total_estimated_min_revenue: 0, total_estimated_max_revenue: 0 })
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Go to Inventory')).toBeInTheDocument()
      })
    })
  })

  // ========================
  // SUMMARY CARD
  // ========================
  describe('Summary Card', () => {
    it('displays Total Potential Revenue label', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Total Potential Revenue')).toBeInTheDocument()
      })
    })

    it('displays total items count', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText(/Analyzing 2 items in your inventory/)).toBeInTheDocument()
      })
    })
  })

  // ========================
  // COMMODITY ANALYSIS CARDS
  // ========================
  describe('Commodity Analysis Cards', () => {
    it('displays commodity names', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Rice')).toBeInTheDocument()
        expect(screen.getByText('Wheat')).toBeInTheDocument()
      })
    })

    it('displays quantity and unit', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('100 kg in inventory')).toBeInTheDocument()
        expect(screen.getByText('50 kg in inventory')).toBeInTheDocument()
      })
    })

    it('displays best recommendation text', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        const recs = screen.getAllByText('Best Recommendation:')
        expect(recs.length).toBeGreaterThanOrEqual(1)
      })
    })

    it('displays recommended mandi name', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        const matches = screen.getAllByText('Thrissur Market')
        expect(matches.length).toBeGreaterThanOrEqual(1)
      })
    })

    it('displays Estimated Revenue label', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        const labels = screen.getAllByText('Estimated Revenue')
        expect(labels.length).toBeGreaterThanOrEqual(1)
      })
    })

    it('displays top mandi card with district and state', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText(/Thrissur, Kerala/)).toBeInTheDocument()
      })
    })

    it('shows Local badge for local mandis', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Local')).toBeInTheDocument()
      })
    })

    it('shows expand button when multiple mandis available', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Show 1 more options')).toBeInTheDocument()
      })
    })

    it('expands to show more mandis on click', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Show 1 more options')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('Show 1 more options'))
      expect(screen.getByText('Ernakulam Market')).toBeInTheDocument()
    })

    it('collapses mandis when clicked again', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Show 1 more options')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('Show 1 more options'))
      expect(screen.getByText('Hide other options')).toBeInTheDocument()
      fireEvent.click(screen.getByText('Hide other options'))
      expect(screen.getByText('Show 1 more options')).toBeInTheDocument()
    })
  })

  // ========================
  // NO PRICE DATA
  // ========================
  describe('No Price Data', () => {
    it('shows no price data message when best_mandis is empty', async () => {
      const noPriceAnalysis = {
        total_items: 1,
        total_estimated_min_revenue: 0,
        total_estimated_max_revenue: 0,
        analysis: [
          {
            commodity_id: 'c3',
            commodity_name: 'Mango',
            quantity: 50,
            unit: 'kg',
            best_mandis: [],
            estimated_min_revenue: 0,
            estimated_max_revenue: 0,
            message: 'No recent price data for Mango.',
          },
        ],
      }
      mockAnalyzeInventory.mockResolvedValue(noPriceAnalysis)
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('No price data available')).toBeInTheDocument()
        expect(screen.getByText('No recent price data for Mango.')).toBeInTheDocument()
      })
    })
  })

  // ========================
  // ACTION BUTTONS
  // ========================
  describe('Action Buttons', () => {
    it('shows Update Inventory button', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Update Inventory')).toBeInTheDocument()
      })
    })

    it('shows Record a Sale button', async () => {
      render(<AnalyzeInventoryPage />)
      await waitFor(() => {
        expect(screen.getByText('Record a Sale')).toBeInTheDocument()
      })
    })
  })
})
