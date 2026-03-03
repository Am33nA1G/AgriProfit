import { render, screen } from "@test/test-utils";
import { vi, describe, it, expect, beforeEach } from "vitest";

// CRITICAL: Stable router mock using vi.hoisted() to prevent infinite render loops
const mockRouter = vi.hoisted(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => mockRouter,
    usePathname: () => "/arbitrage",
}));

// Mock TanStack Query
const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", () => ({
    useQuery: (...args: any[]) => mockUseQuery(...args),
    QueryClient: vi.fn(),
    QueryClientProvider: ({ children }: any) => children,
}));

// Mock arbitrage service
vi.mock("@/services/arbitrage", () => ({
    arbitrageService: {
        getResults: vi.fn(),
    },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn(),
    },
}));

// Import the page under test (will fail RED until page.tsx is created)
import ArbitragePage from "../page";

// Fixture data
const mockArbitrageResult = {
    mandi_name: "Azadpur Mandi",
    district: "North Delhi",
    state: "Delhi",
    distance_km: 120.5,
    travel_time_hours: 3.2,
    freight_cost_per_quintal: 450.0,
    spoilage_percent: 2.1,
    net_profit_per_quintal: 820.5,
    verdict: "excellent",
    is_interstate: false,
    price_date: "2025-10-28",
    days_since_update: 5,
    is_stale: false,
    stale_warning: null,
};

const mockArbitrageResponse = {
    commodity: "Wheat",
    origin_district: "Ernakulam",
    results: [mockArbitrageResult, { ...mockArbitrageResult, mandi_name: "Ghazipur Mandi", net_profit_per_quintal: 650.0, verdict: "good" }],
    suppressed_count: 0,
    threshold_pct: 10,
    data_reference_date: "2025-10-30",
    has_stale_data: false,
    distance_note: null,
};

describe("ArbitragePage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseQuery.mockReturnValue({
            data: undefined,
            isLoading: false,
            error: null,
        });
    });

    it("test_selectors_render: renders commodity and district input placeholders", () => {
        render(<ArbitragePage />);

        expect(screen.getByPlaceholderText(/commodity/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/district/i)).toBeInTheDocument();
    });

    it("test_results_table_shown_on_data: shows results table when query returns data", () => {
        mockUseQuery.mockReturnValue({
            data: mockArbitrageResponse,
            isLoading: false,
            error: null,
        });

        render(<ArbitragePage />);

        expect(screen.getByText("Azadpur Mandi")).toBeInTheDocument();
        expect(screen.getByText("Ghazipur Mandi")).toBeInTheDocument();
    });

    it("test_stale_banner_shown: renders stale data alert when has_stale_data is true", () => {
        mockUseQuery.mockReturnValue({
            data: {
                ...mockArbitrageResponse,
                has_stale_data: true,
                data_reference_date: "2025-10-30",
            },
            isLoading: false,
            error: null,
        });

        render(<ArbitragePage />);

        // The alert contains both "Data last updated" and the date in the same text
        expect(screen.getByText(/Data last updated.*2025-10-30/i)).toBeInTheDocument();
    });

    it("test_suppressed_empty_state: shows margin threshold message when results empty and suppressed_count > 0", () => {
        mockUseQuery.mockReturnValue({
            data: {
                ...mockArbitrageResponse,
                results: [],
                suppressed_count: 3,
            },
            isLoading: false,
            error: null,
        });

        render(<ArbitragePage />);

        expect(screen.getByText(/below the.*margin threshold/i)).toBeInTheDocument();
    });

    it("test_generic_empty_state: shows generic no-opportunities message when results empty and suppressed_count is 0", () => {
        mockUseQuery.mockReturnValue({
            data: {
                ...mockArbitrageResponse,
                results: [],
                suppressed_count: 0,
            },
            isLoading: false,
            error: null,
        });

        render(<ArbitragePage />);

        expect(screen.getByText(/No arbitrage opportunities/i)).toBeInTheDocument();
    });
});
