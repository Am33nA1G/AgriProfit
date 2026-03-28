import { render, screen, waitFor } from "@test/test-utils";
import { vi, describe, it, expect, beforeEach } from "vitest";
import SoilAdvisorPage from "../page";

// ---------------------------------------------------------------------------
// Stable router reference (MEMORY.md: useEffect([router]) requires stable ref)
// ---------------------------------------------------------------------------

const mockRouter = vi.hoisted(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => mockRouter,
    usePathname: () => "/soil-advisor",
    useSearchParams: () => ({ get: vi.fn(() => null) }),
}));

// ---------------------------------------------------------------------------
// Mock TanStack React Query — capture useQuery calls by queryKey
// ---------------------------------------------------------------------------

const mockUseQuery = vi.fn();

vi.mock("@tanstack/react-query", () => ({
    useQuery: (...args: any[]) => mockUseQuery(...args),
    QueryClient: vi.fn(),
    QueryClientProvider: ({ children }: any) => children,
}));

// ---------------------------------------------------------------------------
// Mock soil-advisor service
// ---------------------------------------------------------------------------

vi.mock("@/services/soil-advisor", () => ({
    soilAdvisorApi: {
        getStates: vi.fn(),
        getDistricts: vi.fn(),
        getBlocks: vi.fn(),
        getProfile: vi.fn(),
    },
}));

// ---------------------------------------------------------------------------
// Helper: mock useQuery responses
// ---------------------------------------------------------------------------

const MOCK_STATES = ["ANDHRA PRADESH", "GUJARAT", "KARNATAKA"];
const MOCK_PROFILE = {
    state: "ANDHRA PRADESH",
    district: "ANANTAPUR",
    block: "TEST-BLOCK",
    cycle: "2025-26",
    disclaimer: "Block-average soil data for TEST-BLOCK — not field-level measurement",
    nutrient_distributions: [
        { nutrient: "Nitrogen", high_pct: 0, medium_pct: 4, low_pct: 96 },
        { nutrient: "Phosphorus", high_pct: 81, medium_pct: 17, low_pct: 2 },
        { nutrient: "Potassium", high_pct: 83, medium_pct: 14, low_pct: 3 },
        { nutrient: "Organic Carbon", high_pct: 0, medium_pct: 4, low_pct: 96 },
        { nutrient: "Potential Of Hydrogen", high_pct: 0, medium_pct: 0, low_pct: 100 },
    ],
    crop_recommendations: [
        { crop_name: "Groundnut", suitability_score: 1.97, suitability_rank: 1, seasonal_demand: null },
        { crop_name: "Chickpea", suitability_score: 1.97, suitability_rank: 2, seasonal_demand: "HIGH" },
    ],
    fertiliser_advice: [
        {
            nutrient: "Nitrogen",
            low_pct: 96,
            message: "96% of soils in this block are nitrogen-deficient",
            fertiliser_recommendation: "Urea (46% N) at 120-150 kg/ha for cereals",
        },
    ],
    coverage_gap: false,
};

function mockAllQueriesIdle() {
    mockUseQuery.mockImplementation(() => ({
        data: undefined,
        isLoading: false,
        error: null,
    }));
}

function mockWithStates() {
    mockUseQuery.mockImplementation((options: any) => {
        const key = options?.queryKey?.[0];
        if (key === "soil-advisor-states") {
            return { data: MOCK_STATES, isLoading: false, error: null };
        }
        return { data: undefined, isLoading: false, error: null };
    });
}

function mockWithProfileLoaded() {
    mockUseQuery.mockImplementation((options: any) => {
        const key = options?.queryKey?.[0];
        if (key === "soil-advisor-states") {
            return { data: MOCK_STATES, isLoading: false, error: null };
        }
        if (key === "soil-advisor-districts") {
            return { data: ["ANANTAPUR"], isLoading: false, error: null };
        }
        if (key === "soil-advisor-blocks") {
            return { data: ["TEST-BLOCK"], isLoading: false, error: null };
        }
        if (key === "soil-advisor-profile") {
            return { data: MOCK_PROFILE, isLoading: false, error: null };
        }
        return { data: undefined, isLoading: false, error: null };
    });
}

function mockWithCoverageGapError() {
    const axiosError = {
        response: {
            status: 404,
            data: {
                detail: {
                    coverage_gap: true,
                    message: "Soil data not available for PUNJAB. Available for 21 states only.",
                },
            },
        },
    };
    mockUseQuery.mockImplementation((options: any) => {
        const key = options?.queryKey?.[0];
        if (key === "soil-advisor-states") {
            return { data: MOCK_STATES, isLoading: false, error: null };
        }
        if (key === "soil-advisor-districts") {
            return { data: ["AMRITSAR"], isLoading: false, error: null };
        }
        if (key === "soil-advisor-blocks") {
            return { data: ["AMRITSAR BLOCK"], isLoading: false, error: null };
        }
        if (key === "soil-advisor-profile") {
            return { data: undefined, isLoading: false, error: axiosError };
        }
        return { data: undefined, isLoading: false, error: null };
    });
}

// ---------------------------------------------------------------------------
// Test Suite
// ---------------------------------------------------------------------------

describe("SoilAdvisorPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe("Test 1: SoilDisclaimer renders without dismiss button", () => {
        it("renders disclaimer without dismiss button when profile is loaded", async () => {
            mockWithProfileLoaded();

            render(<SoilAdvisorPage />);

            // Disclaimer text is present
            await waitFor(() => {
                expect(
                    screen.getByText(
                        /Block-average soil data for TEST-BLOCK — not field-level measurement/i
                    )
                ).toBeInTheDocument();
            });

            // There must be NO button with dismiss/close/hide text near the disclaimer
            const buttons = screen.queryAllByRole("button", {
                name: /dismiss|close|hide/i,
            });
            expect(buttons.length).toBe(0);
        });
    });

    describe("Test 2: District select disabled before state selected", () => {
        it("district select is disabled when no state is selected", () => {
            mockAllQueriesIdle();

            render(<SoilAdvisorPage />);

            // The district select should be disabled by default (no state selected)
            const districtSelect = screen.getByTestId("district-select");
            expect(districtSelect).toBeDisabled();
        });
    });

    describe("Test 3: Coverage gap banner shown on 404", () => {
        it("shows coverage gap banner when profile returns 404 coverage_gap error", async () => {
            mockWithCoverageGapError();

            render(<SoilAdvisorPage />);

            // Coverage gap banner must be visible
            await waitFor(() => {
                expect(
                    screen.getByText(/Soil data is not available for this region/i)
                ).toBeInTheDocument();
            });

            // No crop recommendations should be shown
            expect(screen.queryByText("Groundnut")).not.toBeInTheDocument();
            expect(screen.queryByText("Chickpea")).not.toBeInTheDocument();
        });
    });
});
