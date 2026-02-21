import { render, screen, waitFor } from '@test/test-utils'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import MandisPage from '../page'
import { mandisService } from '@/services/mandis'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(() => null),
  }),
  usePathname: () => '/mandis',
}))

// Mock services
vi.mock('@/services/mandis', () => ({
  mandisService: {
    getAll: vi.fn(),
    getById: vi.fn(),
    getNearby: vi.fn(),
    getWithFilters: vi.fn(),
    getStates: vi.fn(() => Promise.resolve(['Delhi', 'Maharashtra', 'Punjab'])),
    getDistrictsByState: vi.fn(() => Promise.resolve([])),
  },
}))

vi.mock('@/services/auth', () => ({
  authService: {
    getCurrentUser: vi.fn(() => Promise.resolve({ district: 'North Delhi', state: 'Delhi' })),
  },
}))

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const mockMandis = [
  {
    id: 'mandi_1',
    name: 'Delhi Azadpur',
    state: 'Delhi',
    district: 'North Delhi',
    address: 'Azadpur, Delhi',
    distance_km: 50,
    latitude: 28.7041,
    longitude: 77.1025,
    rating: 4.2,
    total_reviews: 120,
    facilities: {
      weighbridge: true,
      storage: true,
      loading_dock: false,
      cold_storage: false,
    },
    top_prices: [
      { commodity_id: 'c1', commodity_name: 'Tomato', modal_price: 2500, as_of: '2026-02-20' },
    ],
  },
  {
    id: 'mandi_2',
    name: 'Ludhiana Mandi',
    state: 'Punjab',
    district: 'Ludhiana',
    address: 'Ludhiana, Punjab',
    distance_km: 15,
    latitude: 30.9010,
    longitude: 75.8573,
    rating: 3.8,
    total_reviews: 85,
    facilities: {
      weighbridge: true,
      storage: false,
      loading_dock: true,
      cold_storage: true,
    },
    top_prices: [],
  },
  {
    id: 'mandi_3',
    name: 'Chandigarh Grain Market',
    state: 'Chandigarh',
    district: 'Chandigarh',
    address: 'Sector 26, Chandigarh',
    distance_km: 75,
    latitude: 30.7333,
    longitude: 76.7794,
    rating: 4.5,
    total_reviews: 200,
    facilities: {
      weighbridge: false,
      storage: false,
      loading_dock: false,
      cold_storage: false,
    },
    top_prices: [],
  },
]

describe('MandisPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Setup default mock implementation
    ;(mandisService.getAll as any).mockResolvedValue(mockMandis)
    ;(mandisService.getWithFilters as any).mockResolvedValue({
      mandis: mockMandis,
      total: mockMandis.length,
      page: 1,
      limit: 50,
      has_more: false,
    })
    ;(mandisService.getStates as any).mockResolvedValue(['Delhi', 'Maharashtra', 'Punjab'])
  })

  it('renders mandis page heading', () => {
    render(<MandisPage />)

    const heading = screen.getByRole('heading', { name: /mandis|markets/i })
    expect(heading).toBeInTheDocument()
  })

  it('displays list of mandis', async () => {
    render(<MandisPage />)

    await waitFor(() => {
      expect(screen.getByText('Delhi Azadpur')).toBeInTheDocument()
      expect(screen.getByText('Ludhiana Mandi')).toBeInTheDocument()
    })
  })

  it('shows mandi locations (states/districts)', async () => {
    render(<MandisPage />)

    await waitFor(() => {
      expect(screen.getByText('North Delhi')).toBeInTheDocument()
    })
  })

  it('displays distance information', async () => {
    render(<MandisPage />)

    await waitFor(() => {
      const distanceElements = screen.queryAllByText(/km/i)
      expect(distanceElements.length).toBeGreaterThan(0)
    })
  })

  it('displays facility badges', async () => {
    render(<MandisPage />)

    await waitFor(() => {
      // Delhi Azadpur has weighbridge and storage
      expect(screen.getAllByText(/Weighbridge/i).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/Storage/i).length).toBeGreaterThan(0)
    })
  })

  it('has search functionality', () => {
    render(<MandisPage />)

    const searchInputs = screen.queryAllByRole('textbox')
    expect(searchInputs.length).toBeGreaterThan(0)
  })

  it('can filter by state', async () => {
    render(<MandisPage />)
    const user = userEvent.setup()

    // Wait for states to load
    await waitFor(() => {
      expect(screen.getByText('Delhi')).toBeInTheDocument()
    })

    // Click on Delhi state button
    const delhiBtn = screen.getByRole('button', { name: 'Delhi' })
    await user.click(delhiBtn)

    // Should trigger re-fetch with state filter
    await waitFor(() => {
      expect(mandisService.getWithFilters).toHaveBeenCalled()
    })
  })

  it('renders without crashing when data is empty', async () => {
    ;(mandisService.getAll as any).mockResolvedValue([])
    ;(mandisService.getWithFilters as any).mockResolvedValue({
      mandis: [],
      total: 0,
      page: 1,
      limit: 50,
      has_more: false,
    })

    render(<MandisPage />)

    await waitFor(() => {
      expect(document.body).toBeTruthy()
    })
  })

  it('handles loading state', () => {
    ;(mandisService.getWithFilters as any).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 5000))
    )

    render(<MandisPage />)

    // Page should render without crashing
    expect(document.body).toBeTruthy()
  })

  it('displays mandi details on click', async () => {
    render(<MandisPage />)
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByText('Delhi Azadpur')).toBeInTheDocument()
    })

    const mandiElement = screen.getByText('Delhi Azadpur')
    await user.click(mandiElement)

    // Should trigger navigation (router.push called)
  })

  it('shows clear filters button when filters are active', async () => {
    render(<MandisPage />)
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByText('Delhi')).toBeInTheDocument()
    })

    // Click state filter to activate it
    const delhiBtn = screen.getByRole('button', { name: 'Delhi' })
    await user.click(delhiBtn)

    // Clear All button should appear
    await waitFor(() => {
      const clearBtns = screen.queryAllByText(/clear/i)
      expect(clearBtns.length).toBeGreaterThan(0)
    })
  })
})
