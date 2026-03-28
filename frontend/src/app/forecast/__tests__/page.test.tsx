import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@test/test-utils'

// Stable router reference (critical — prevents infinite re-renders if router in useEffect deps)
const mockRouter = {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
}

// Override the global setup.ts mock with stable router
vi.mock('next/navigation', () => ({
    useRouter: () => mockRouter,
    usePathname: () => '/',
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
}))

// Mock lucide-react with explicit named exports (never Proxy — see MEMORY.md)
vi.mock('lucide-react', () => ({
    TrendingUp: ({ className }: any) => <span className={className}>TrendingUp</span>,
    TrendingDown: ({ className }: any) => <span className={className}>TrendingDown</span>,
    ArrowRight: ({ className }: any) => <span className={className}>ArrowRight</span>,
    AlertTriangle: ({ className }: any) => <span className={className}>AlertTriangle</span>,
    BarChart3: ({ className }: any) => <span className={className}>BarChart3</span>,
    Loader2: ({ className }: any) => <span className={className}>Loader2</span>,
    Info: ({ className }: any) => <span className={className}>Info</span>,
    Lock: ({ className }: any) => <span className={className}>Lock</span>,
}))

// Mock ForecastChart with a stable testid div
vi.mock('@/components/ForecastChart', () => ({
    default: ({ forecastPoints }: any) => (
        <div data-testid="forecast-chart">chart ({forecastPoints?.length ?? 0} points)</div>
    ),
}))

// Mock forecastService
vi.mock('@/services/forecast', () => ({
    forecastService: {
        getCommodities: vi.fn().mockResolvedValue(['tomato', 'onion']),
        getCommoditiesForDistrict: vi.fn().mockResolvedValue(['tomato', 'onion']),
        getForecast: vi.fn(),
    },
}))

import ForecastPage from '../page'
import { forecastService } from '@/services/forecast'

// ---------------------------------------------------------------------------
// Shared mock data fixtures
// ---------------------------------------------------------------------------

const BASE_FORECAST = {
    commodity: 'tomato',
    district: 'Pune',
    horizon_days: 14,
    direction: 'up' as const,
    price_low: 1800,
    price_mid: 2000,
    price_high: 2200,
    confidence_colour: 'Green' as const,
    tier_label: 'full model',
    last_data_date: '2025-10-30',
    forecast_points: [
        { date: '2025-11-01', price_low: 1800, price_mid: 2000, price_high: 2200 },
    ],
    coverage_message: null,
    r2_score: 0.6,
}

// PROD-05: stale banner — is_stale=true, data_freshness_days=45
const STALE_FORECAST = {
    ...BASE_FORECAST,
    // Phase 7 new fields not yet in TS interface — cast suppresses error
    is_stale: true,
    data_freshness_days: 45,
    n_markets: 8,
    typical_error_inr: 200,
} as any

// PROD-02: chart hidden when confidence_colour=Red
const RED_CONFIDENCE_FORECAST = {
    ...BASE_FORECAST,
    confidence_colour: 'Red' as const,
    // Non-empty forecast_points — chart would normally render, but should be hidden
    forecast_points: [
        { date: '2025-11-01', price_low: 1200, price_mid: 1400, price_high: 1600 },
        { date: '2025-11-02', price_low: 1180, price_mid: 1390, price_high: 1590 },
    ],
    is_stale: false,
    data_freshness_days: 5,
    n_markets: 2,
    typical_error_inr: null,
} as any

// PROD-03: uncertain direction badge
const UNCERTAIN_DIRECTION_FORECAST = {
    ...BASE_FORECAST,
    direction: 'uncertain', // not in TS union yet — use as any
    confidence_colour: 'Yellow' as const,
    is_stale: false,
    data_freshness_days: 10,
    n_markets: 5,
    typical_error_inr: 300,
} as any

// ---------------------------------------------------------------------------
// Helper: select commodity + district to trigger canFetch=true
// ---------------------------------------------------------------------------
async function selectCommodityAndDistrict() {
    // Wait for commodity list to load (getCommodities resolves)
    await waitFor(() => {
        expect(screen.getByText('Tomato')).toBeInTheDocument()
    })

    // Select commodity
    fireEvent.change(screen.getByRole('combobox', { name: /commodity/i }) || document.getElementById('commodity-select')!, {
        target: { value: 'tomato' },
    })

    // Select state first (district select is disabled without state)
    fireEvent.change(document.getElementById('state-select')!, {
        target: { value: 'Maharashtra' },
    })

    // Select district (Pune is in Maharashtra)
    fireEvent.change(document.getElementById('district-select')!, {
        target: { value: 'Pune' },
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ForecastPage — Phase 7 RED stubs', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(forecastService.getCommodities).mockResolvedValue(['tomato', 'onion'])
        vi.mocked(forecastService.getCommoditiesForDistrict).mockResolvedValue(['tomato', 'onion'])
    })

    // -----------------------------------------------------------------------
    // PROD-05: Stale data banner
    // -----------------------------------------------------------------------
    it('stale_banner_renders_when_is_stale: shows stale data banner when is_stale=true', async () => {
        vi.mocked(forecastService.getForecast).mockResolvedValue(STALE_FORECAST)

        render(<ForecastPage />)

        // Select state → district → commodity (district selection resets commodity)
        fireEvent.change(document.getElementById('state-select')!, {
            target: { value: 'Maharashtra' },
        })
        fireEvent.change(document.getElementById('district-select')!, {
            target: { value: 'Pune' },
        })
        // Wait for district commodities to load, then select commodity
        await waitFor(() => {
            expect(screen.getByText('Tomato')).toBeInTheDocument()
        })
        fireEvent.change(document.getElementById('commodity-select')!, {
            target: { value: 'tomato' },
        })

        // Wait for forecast result to render
        await waitFor(() => {
            expect(screen.getByText('RISING')).toBeInTheDocument()
        })

        expect(screen.getByTestId('stale-data-banner')).toBeInTheDocument()
    })

    // -----------------------------------------------------------------------
    // PROD-02: Chart hidden when confidence = Red
    // -----------------------------------------------------------------------
    it('chart_hidden_when_confidence_red: forecast chart is not rendered when confidence_colour=Red', async () => {
        vi.mocked(forecastService.getForecast).mockResolvedValue(RED_CONFIDENCE_FORECAST)

        render(<ForecastPage />)

        // Select state → district → commodity (district selection resets commodity)
        fireEvent.change(document.getElementById('state-select')!, {
            target: { value: 'Maharashtra' },
        })
        fireEvent.change(document.getElementById('district-select')!, {
            target: { value: 'Pune' },
        })
        await waitFor(() => {
            expect(screen.getByText('Tomato')).toBeInTheDocument()
        })
        fireEvent.change(document.getElementById('commodity-select')!, {
            target: { value: 'tomato' },
        })

        // Wait for forecast result to render
        await waitFor(() => {
            expect(screen.getByText('Low Confidence')).toBeInTheDocument()
        })

        expect(screen.queryByTestId('forecast-chart')).not.toBeInTheDocument()
    })

    // -----------------------------------------------------------------------
    // PROD-03: Uncertain direction badge
    // -----------------------------------------------------------------------
    it('uncertain_badge_renders: shows Uncertain badge when direction=uncertain', async () => {
        vi.mocked(forecastService.getForecast).mockResolvedValue(UNCERTAIN_DIRECTION_FORECAST)

        render(<ForecastPage />)

        // Select state → district → commodity (district selection resets commodity)
        fireEvent.change(document.getElementById('state-select')!, {
            target: { value: 'Maharashtra' },
        })
        fireEvent.change(document.getElementById('district-select')!, {
            target: { value: 'Pune' },
        })
        await waitFor(() => {
            expect(screen.getByText('Tomato')).toBeInTheDocument()
        })
        fireEvent.change(document.getElementById('commodity-select')!, {
            target: { value: 'tomato' },
        })

        // Wait for forecast result to render
        await waitFor(() => {
            expect(screen.getByText('Directional only')).toBeInTheDocument()
        })

        expect(screen.getByText('UNCERTAIN')).toBeInTheDocument()
    })
})
