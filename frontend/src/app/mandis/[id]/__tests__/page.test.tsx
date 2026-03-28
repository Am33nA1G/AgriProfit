import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import MandiDetailPage from '../page'

// ---------- Mocks ----------

const mockPush = vi.fn()
const mockBack = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, back: mockBack, replace: vi.fn(), refresh: vi.fn(), prefetch: vi.fn(), forward: vi.fn() }),
  usePathname: () => '/mandis/test-mandi-id',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: 'test-mandi-id' }),
}))

vi.mock('@/services/mandis', () => ({
  mandisService: {
    getDetails: vi.fn(),
  },
}))

vi.mock('@/services/auth', () => ({
  authService: {
    getCurrentUser: vi.fn().mockResolvedValue({ district: 'Thrissur', state: 'Kerala' }),
  },
}))

vi.mock('@/components/layout/AppLayout', () => ({
  AppLayout: ({ children }: any) => <div data-testid="app-layout">{children}</div>,
}))

// --- React Query mock ---

const mockMandi = {
  id: 'test-mandi-id',
  name: 'Thrissur Main Market',
  state: 'Kerala',
  district: 'Thrissur',
  address: '123 Market Road, Thrissur',
  market_code: 'KL-TSR-001',
  pincode: '680001',
  location: {
    latitude: 10.5276,
    longitude: 76.2144,
  },
  contact: {
    phone: '0487-2320123',
    email: 'thrissur@mandi.gov.in',
    website: 'https://thrissur-mandi.gov.in',
  },
  operating_hours: {
    opening_time: '06:00 AM',
    closing_time: '06:00 PM',
    operating_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
  },
  facilities: {
    weighbridge: true,
    storage: true,
    loading_dock: false,
    cold_storage: true,
  },
  payment_methods: ['Cash', 'UPI', 'Bank Transfer'],
  commodities_accepted: ['Rice', 'Wheat', 'Tomato', 'Onion'],
  rating: 4.2,
  total_reviews: 56,
  distance_km: 12.5,
  current_prices: [
    { commodity_id: 'c1', commodity_name: 'Rice', modal_price: 2500.0, as_of: '2026-01-15T10:00:00Z' },
    { commodity_id: 'c2', commodity_name: 'Wheat', modal_price: 2200.5, as_of: '2026-01-15T10:00:00Z' },
  ],
}

let queryOverrides: Record<string, any> = {}

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn((opts: any) => {
    const key = Array.isArray(opts.queryKey) ? opts.queryKey[0] : opts.queryKey
    if (queryOverrides[key]) return queryOverrides[key]
    if (key === 'mandi-detail') return { data: mockMandi, isLoading: false, error: null }
    return { data: undefined, isLoading: false, error: null }
  }),
  useMutation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useQueryClient: vi.fn(() => ({
    invalidateQueries: vi.fn(),
  })),
}))

// ---------- Tests ----------

describe('MandiDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    queryOverrides = {}
  })

  // ========================
  // LOADING STATE
  // ========================
  describe('Loading State', () => {
    it('shows loading spinner when data is loading', () => {
      queryOverrides['mandi-detail'] = { data: undefined, isLoading: true, error: null }
      render(<MandiDetailPage />)
      expect(screen.getByText('Loading mandi details...')).toBeInTheDocument()
    })

    it('renders within AppLayout during loading', () => {
      queryOverrides['mandi-detail'] = { data: undefined, isLoading: true, error: null }
      render(<MandiDetailPage />)
      expect(screen.getByTestId('app-layout')).toBeInTheDocument()
    })
  })

  // ========================
  // ERROR STATE
  // ========================
  describe('Error State', () => {
    it('shows Mandi Not Found on error', () => {
      queryOverrides['mandi-detail'] = { data: undefined, isLoading: false, error: new Error('Not found') }
      render(<MandiDetailPage />)
      expect(screen.getByText('Mandi Not Found')).toBeInTheDocument()
    })

    it('shows error description text', () => {
      queryOverrides['mandi-detail'] = { data: undefined, isLoading: false, error: new Error('err') }
      render(<MandiDetailPage />)
      expect(screen.getByText(/doesn't exist or has been removed/)).toBeInTheDocument()
    })

    it('shows Go Back button on error', () => {
      queryOverrides['mandi-detail'] = { data: undefined, isLoading: false, error: new Error('err') }
      render(<MandiDetailPage />)
      expect(screen.getByText('Go Back')).toBeInTheDocument()
    })

    it('calls router.back on Go Back click', () => {
      queryOverrides['mandi-detail'] = { data: undefined, isLoading: false, error: new Error('err') }
      render(<MandiDetailPage />)
      fireEvent.click(screen.getByText('Go Back'))
      expect(mockBack).toHaveBeenCalled()
    })

    it('shows Mandi Not Found when data is null', () => {
      queryOverrides['mandi-detail'] = { data: null, isLoading: false, error: null }
      render(<MandiDetailPage />)
      expect(screen.getByText('Mandi Not Found')).toBeInTheDocument()
    })
  })

  // ========================
  // HEADER
  // ========================
  describe('Header', () => {
    it('displays mandi name', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Thrissur Main Market')).toBeInTheDocument()
    })

    it('displays market code', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Code: KL-TSR-001')).toBeInTheDocument()
    })

    it('displays district and state badge', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Thrissur, Kerala')).toBeInTheDocument()
    })

    it('displays rating badge', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('4.2 (56 reviews)')).toBeInTheDocument()
    })

    it('displays distance badge', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('12.5 km away')).toBeInTheDocument()
    })

    it('shows Back to Mandis button', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Back to Mandis')).toBeInTheDocument()
    })

    it('calls router.back on Back to Mandis click', () => {
      render(<MandiDetailPage />)
      fireEvent.click(screen.getByText('Back to Mandis'))
      expect(mockBack).toHaveBeenCalled()
    })

    it('renders within AppLayout', () => {
      render(<MandiDetailPage />)
      expect(screen.getByTestId('app-layout')).toBeInTheDocument()
    })
  })

  // ========================
  // CONTACT INFORMATION
  // ========================
  describe('Contact Information', () => {
    it('displays Contact Information title', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Contact Information')).toBeInTheDocument()
    })

    it('displays contact description', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Get in touch with this mandi')).toBeInTheDocument()
    })

    it('displays address', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('123 Market Road, Thrissur')).toBeInTheDocument()
    })

    it('displays pincode', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('PIN: 680001')).toBeInTheDocument()
    })

    it('displays phone number', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('0487-2320123')).toBeInTheDocument()
    })

    it('displays email', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('thrissur@mandi.gov.in')).toBeInTheDocument()
    })

    it('displays website', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('https://thrissur-mandi.gov.in')).toBeInTheDocument()
    })

    it('shows no contact message when no contact info', () => {
      const mandiNoContact = {
        ...mockMandi,
        contact: { phone: null, email: null, website: null },
        address: null,
        pincode: null,
      }
      queryOverrides['mandi-detail'] = { data: mandiNoContact, isLoading: false, error: null }
      render(<MandiDetailPage />)
      expect(screen.getByText('No contact information available')).toBeInTheDocument()
    })
  })

  // ========================
  // OPERATING HOURS
  // ========================
  describe('Operating Hours', () => {
    it('displays Operating Hours title', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Operating Hours')).toBeInTheDocument()
    })

    it('displays timing', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('06:00 AM - 06:00 PM')).toBeInTheDocument()
    })

    it('displays operating days', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Monday')).toBeInTheDocument()
      expect(screen.getByText('Saturday')).toBeInTheDocument()
    })

    it('displays Operating Days label', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Operating Days')).toBeInTheDocument()
    })

    it('displays Timing label', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Timing')).toBeInTheDocument()
    })
  })

  // ========================
  // CURRENT PRICES
  // ========================
  describe('Current Prices', () => {
    it('displays Current Prices title', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Current Prices')).toBeInTheDocument()
    })

    it('displays price description', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Latest commodity prices at this mandi')).toBeInTheDocument()
    })

    it('displays commodity names', () => {
      render(<MandiDetailPage />)
      // The "Rice" and "Wheat" in current_prices
      const riceEls = screen.getAllByText('Rice')
      expect(riceEls.length).toBeGreaterThanOrEqual(1)
    })

    it('displays modal prices', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('₹2500.00')).toBeInTheDocument()
      expect(screen.getByText('₹2200.50')).toBeInTheDocument()
    })

    it('displays per quintal label', () => {
      render(<MandiDetailPage />)
      const labels = screen.getAllByText('per quintal')
      expect(labels.length).toBeGreaterThanOrEqual(2)
    })
  })

  // ========================
  // COMMODITIES ACCEPTED
  // ========================
  describe('Accepted Commodities', () => {
    it('displays Accepted Commodities title', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Accepted Commodities')).toBeInTheDocument()
    })

    it('displays commodity badges', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Tomato')).toBeInTheDocument()
      expect(screen.getByText('Onion')).toBeInTheDocument()
    })

    it('displays description', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Commodities traded at this market')).toBeInTheDocument()
    })
  })

  // ========================
  // FACILITIES
  // ========================
  describe('Facilities', () => {
    it('displays Facilities title', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Facilities')).toBeInTheDocument()
    })

    it('displays facility names', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Weighbridge')).toBeInTheDocument()
      expect(screen.getByText('Storage')).toBeInTheDocument()
      expect(screen.getByText('Loading Dock')).toBeInTheDocument()
      expect(screen.getByText('Cold Storage')).toBeInTheDocument()
    })

    it('shows Available badges for enabled facilities', () => {
      render(<MandiDetailPage />)
      // weighbridge, storage, cold_storage are true = 3 Available badges
      const badges = screen.getAllByText('Available')
      expect(badges.length).toBe(3)
    })

    it('displays Available amenities description', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Available amenities')).toBeInTheDocument()
    })
  })

  // ========================
  // PAYMENT METHODS
  // ========================
  describe('Payment Methods', () => {
    it('displays Payment Methods title', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Payment Methods')).toBeInTheDocument()
    })

    it('displays payment method names', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Cash')).toBeInTheDocument()
      expect(screen.getByText('UPI')).toBeInTheDocument()
      expect(screen.getByText('Bank Transfer')).toBeInTheDocument()
    })

    it('displays accepted payment options description', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Accepted payment options')).toBeInTheDocument()
    })
  })

  // ========================
  // LOCATION
  // ========================
  describe('Location', () => {
    it('displays Location title', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Location')).toBeInTheDocument()
    })

    it('displays latitude', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('10.527600')).toBeInTheDocument()
    })

    it('displays longitude', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('76.214400')).toBeInTheDocument()
    })

    it('displays Latitude label', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Latitude:')).toBeInTheDocument()
    })

    it('displays Longitude label', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Longitude:')).toBeInTheDocument()
    })

    it('displays Open in Google Maps button', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Open in Google Maps')).toBeInTheDocument()
    })

    it('displays Geographic coordinates description', () => {
      render(<MandiDetailPage />)
      expect(screen.getByText('Geographic coordinates')).toBeInTheDocument()
    })

    it('opens Google Maps on button click', () => {
      const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
      render(<MandiDetailPage />)
      fireEvent.click(screen.getByText('Open in Google Maps'))
      expect(openSpy).toHaveBeenCalledWith(
        expect.stringContaining('google.com/maps'),
        '_blank'
      )
      openSpy.mockRestore()
    })
  })

  // ========================
  // NO OPTIONAL DATA
  // ========================
  describe('Missing Optional Data', () => {
    const minimalMandi = {
      ...mockMandi,
      market_code: null,
      rating: null,
      total_reviews: 0,
      distance_km: null,
      current_prices: [],
      commodities_accepted: [],
      payment_methods: [],
      location: { latitude: null, longitude: null },
      operating_hours: { opening_time: null, closing_time: null, operating_days: [] },
    }

    it('does not show market code when absent', () => {
      queryOverrides['mandi-detail'] = { data: minimalMandi, isLoading: false, error: null }
      render(<MandiDetailPage />)
      expect(screen.queryByText(/Code:/)).not.toBeInTheDocument()
    })

    it('does not show rating when absent', () => {
      queryOverrides['mandi-detail'] = { data: minimalMandi, isLoading: false, error: null }
      render(<MandiDetailPage />)
      expect(screen.queryByText(/reviews/)).not.toBeInTheDocument()
    })

    it('does not show distance when absent', () => {
      queryOverrides['mandi-detail'] = { data: minimalMandi, isLoading: false, error: null }
      render(<MandiDetailPage />)
      expect(screen.queryByText(/km away/)).not.toBeInTheDocument()
    })

    it('does not show Current Prices section when empty', () => {
      queryOverrides['mandi-detail'] = { data: minimalMandi, isLoading: false, error: null }
      render(<MandiDetailPage />)
      expect(screen.queryByText('Current Prices')).not.toBeInTheDocument()
    })

    it('does not show Payment Methods section when empty', () => {
      queryOverrides['mandi-detail'] = { data: minimalMandi, isLoading: false, error: null }
      render(<MandiDetailPage />)
      expect(screen.queryByText('Payment Methods')).not.toBeInTheDocument()
    })

    it('does not show Location section when coordinates absent', () => {
      queryOverrides['mandi-detail'] = { data: minimalMandi, isLoading: false, error: null }
      render(<MandiDetailPage />)
      expect(screen.queryByText('Geographic coordinates')).not.toBeInTheDocument()
    })
  })
})
