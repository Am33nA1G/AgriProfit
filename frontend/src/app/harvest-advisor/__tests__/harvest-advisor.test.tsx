import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@test/test-utils'

// Mock the service
vi.mock('@/services/harvest-advisor', () => ({
  getRecommendation: vi.fn().mockResolvedValue(null),
  getWeatherWarnings: vi.fn().mockResolvedValue([]),
  getHarvestAdvisorDistricts: vi.fn().mockResolvedValue([]),
}))

// Mock api for the states fetch (soil-advisor endpoint)
vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

// Mock useRouter to avoid infinite re-renders (CRITICAL: stable reference)
const mockRouter = { push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }
vi.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => ({ get: vi.fn() }),
  usePathname: () => '/',
}))

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import HarvestAdvisorPage from '../page'

describe('HarvestAdvisorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page title', () => {
    render(<HarvestAdvisorPage />)
    expect(screen.getByText(/harvest advisor/i)).toBeTruthy()
  })

  it('renders state selector', () => {
    render(<HarvestAdvisorPage />)
    expect(screen.getByLabelText(/state/i)).toBeTruthy()
  })

  it('renders get recommendations button', () => {
    render(<HarvestAdvisorPage />)
    expect(screen.getByRole('button', { name: /get recommendations/i })).toBeTruthy()
  })
})
