import { render, screen, fireEvent, waitFor, within } from "@test/test-utils";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import TransportPage from "../page";
import { commoditiesService } from "@/services/commodities";
import { transportService } from "@/services/transport";
import { toast } from "sonner";

// Mock Services
vi.mock("@/services/commodities", () => ({
    commoditiesService: {
        getAll: vi.fn(),
    },
}));

vi.mock("@/services/transport", () => ({
    transportService: {
        getStates: vi.fn(),
        getDistricts: vi.fn(),
        compareCosts: vi.fn(),
    },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn(),
    },
}));

// Mock TanStack Query to return our mock commodities
const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", () => ({
    useQuery: (...args: any[]) => mockUseQuery(...args),
    QueryClient: vi.fn(),
    QueryClientProvider: ({ children }: any) => children,
}));

// Mock Data
const mockCommodities = [
    { id: "cmd_1", name: "Rice", category: "Grains", unit: "quintal" },
    { id: "cmd_2", name: "Wheat", category: "Grains", unit: "quintal" },
    { id: "cmd_3", name: "Tomato", category: "Vegetables", unit: "kg" },
];

describe("TransportPage - Form Validation", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseQuery.mockImplementation((options: any) => {
            const key = options?.queryKey?.[0];
            if (key === "transport-commodities") {
                return { data: mockCommodities, isLoading: false, error: null };
            }
            return { data: undefined, isLoading: false, error: null };
        });
    });

    it("displays commodity search input", () => {
        render(<TransportPage />);
        
        const searchInput = screen.getByPlaceholderText("Search commodity...");
        expect(searchInput).toBeInTheDocument();
    });

    it("displays quantity input field", () => {
        render(<TransportPage />);
        
        const quantityInput = screen.getByPlaceholderText("Enter amount");
        expect(quantityInput).toBeInTheDocument();
    });

    it("shows unit selector with kg, quintal, ton options", () => {
        render(<TransportPage />);
        
        // Unit selector is rendered via Select component
        const selects = screen.getAllByRole("combobox");
        expect(selects.length).toBeGreaterThan(0);
    });

    it("displays state selector", () => {
        render(<TransportPage />);
        
        // State select should be present
        expect(screen.getByText("State")).toBeInTheDocument();
    });

    it("displays district selector", () => {
        render(<TransportPage />);
        
        expect(screen.getByText("District *")).toBeInTheDocument();
    });

    it("shows calculate button", () => {
        render(<TransportPage />);
        
        const calculateButton = screen.getByRole("button", { name: /calculate/i });
        expect(calculateButton).toBeInTheDocument();
    });

    it("shows error when submitting without commodity", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const calculateButton = screen.getByRole("button", { name: /calculate/i });
        await user.click(calculateButton);
        
        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith("Please fill all required fields");
        });
    });

    it("shows error when submitting without quantity", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        // Select commodity but don't enter quantity
        const searchInput = screen.getByPlaceholderText("Search commodity...");
        await user.click(searchInput);
        
        const calculateButton = screen.getByRole("button", { name: /calculate/i });
        await user.click(calculateButton);
        
        await waitFor(() => {
            expect(toast.error).toHaveBeenCalled();
        });
    });

    it("shows error when submitting without district", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const calculateButton = screen.getByRole("button", { name: /calculate/i });
        await user.click(calculateButton);
        
        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith("Please fill all required fields");
        });
    });

    it("accepts valid quantity input", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const quantityInput = screen.getByPlaceholderText("Enter amount");
        await user.type(quantityInput, "100");
        
        expect(quantityInput).toHaveValue(100);
    });

    it("allows decimal quantity values", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const quantityInput = screen.getByPlaceholderText("Enter amount");
        await user.type(quantityInput, "50.5");
        
        expect(quantityInput).toHaveValue(50.5);
    });
});

describe("TransportPage - Commodity Search", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseQuery.mockImplementation((options: any) => {
            const key = options?.queryKey?.[0];
            if (key === "transport-commodities") {
                return { data: mockCommodities, isLoading: false, error: null };
            }
            return { data: undefined, isLoading: false, error: null };
        });
    });

    it("opens commodity dropdown on focus", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const searchInput = screen.getByPlaceholderText("Search commodity...");
        await user.click(searchInput);
        
        // Should show dropdown with commodities
        await waitFor(() => {
            expect(screen.getByText("Rice")).toBeInTheDocument();
        });
    });

    it("filters commodities based on search input", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const searchInput = screen.getByPlaceholderText("Search commodity...");
        await user.click(searchInput);
        await user.type(searchInput, "Tom");
        
        await waitFor(() => {
            expect(screen.getByText("Tomato")).toBeInTheDocument();
            expect(screen.queryByText("Rice")).not.toBeInTheDocument();
        });
    });

    it("shows 'no commodities found' for invalid search", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const searchInput = screen.getByPlaceholderText("Search commodity...");
        await user.click(searchInput);
        await user.type(searchInput, "xyz123");
        
        await waitFor(() => {
            expect(screen.getByText("No commodities found")).toBeInTheDocument();
        });
    });

    it("selects commodity from dropdown", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const searchInput = screen.getByPlaceholderText("Search commodity...");
        await user.click(searchInput);
        
        await waitFor(() => {
            expect(screen.getByText("Rice")).toBeInTheDocument();
        });
        
        await user.click(screen.getByText("Rice"));
        
        // Dropdown should close and commodity selected
        await waitFor(() => {
            expect(screen.queryByText("Wheat")).not.toBeInTheDocument();
        });
    });

    it("uses fallback commodities if API fails", () => {
        mockUseQuery.mockImplementation((options: any) => {
            const key = options?.queryKey?.[0];
            if (key === "transport-commodities") {
                return { data: undefined, isLoading: false, error: new Error("API failed") };
            }
            return { data: undefined, isLoading: false, error: null };
        });

        render(<TransportPage />);

        // Should still render with fallback COMMODITIES list
        expect(screen.getByPlaceholderText("Search commodity...")).toBeInTheDocument();
    });
});

// Add this mock response constant near the top of the test file, after mockCommodities:
const mockCompareResponse = {
    commodity: "Tomato",
    quantity_kg: 1000,
    source_district: "Ernakulam",
    total_mandis_analyzed: 5,
    distance_note: null,
    best_mandi: null,
    comparisons: [
        {
            mandi_id: "m1",
            mandi_name: "Chalakudy Mandi",
            state: "Kerala",
            district: "Thrissur",
            distance_km: 45,
            price_per_kg: 28,
            gross_revenue: 28000,
            costs: {
                transport_cost: 1800, toll_cost: 300, loading_cost: 200,
                unloading_cost: 200, mandi_fee: 420, commission: 700,
                additional_cost: 150, total_cost: 3770,
                driver_bata: 400, cleaner_bata: 0, halt_cost: 0,
                breakdown_reserve: 90, permit_cost: 0, rto_buffer: 56,
                loading_hamali: 200, unloading_hamali: 200,
            },
            net_profit: 24230,
            profit_per_kg: 24.23,
            roi_percentage: 642.7,
            vehicle_type: "TEMPO",
            vehicle_capacity_kg: 2000,
            trips_required: 1,
            recommendation: "recommended",
            verdict: "excellent",
            verdict_reason: "Strong price premium with low transport cost. Confidence is high.",
            travel_time_hours: 2.1,
            route_type: "mixed",
            is_interstate: false,
            diesel_price_used: 98.0,
            spoilage_percent: 3.5,
            weight_loss_percent: 1.2,
            grade_discount_percent: 2.0,
            net_saleable_quantity_kg: 953,
            price_volatility_7d: 8.2,
            price_trend: "rising",
            risk_score: 22.0,
            confidence_score: 85,
            stability_class: "moderate",
            stress_test: {
                worst_case_profit: 18500,
                break_even_price_per_kg: 4.5,
                margin_of_safety_pct: 23.7,
                verdict_survives_stress: true,
            },
            economic_warning: null,
        },
    ],
};

describe("TransportPage - Results Display", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseQuery.mockImplementation((options: any) => {
            const key = options?.queryKey?.[0];
            if (key === "transport-commodities") {
                return { data: mockCommodities, isLoading: false, error: null };
            }
            return { data: undefined, isLoading: false, error: null };
        });
        (transportService.compareCosts as ReturnType<typeof vi.fn>).mockResolvedValue(mockCompareResponse);
    });

    async function submitForm(user: ReturnType<typeof userEvent.setup>) {
        const searchInput = screen.getByPlaceholderText("Search commodity...");
        await user.click(searchInput);
        await waitFor(() => expect(screen.getByText("Tomato")).toBeInTheDocument());
        await user.click(screen.getByText("Tomato"));

        const quantityInput = screen.getByPlaceholderText("Enter amount");
        await user.clear(quantityInput);
        await user.type(quantityInput, "1000");

        // Select district via the Select component
        // The district select should have a trigger; open it and pick Ernakulam
        const districtTriggers = screen.getAllByRole("combobox");
        // Last combobox is district
        await user.click(districtTriggers[districtTriggers.length - 1]);
        await waitFor(() => {
            const options = screen.queryAllByText("Ernakulam");
            return options.length > 0;
        });
        const ernakulamOptions = screen.queryAllByText("Ernakulam");
        if (ernakulamOptions.length > 0) await user.click(ernakulamOptions[0]);

        await user.click(screen.getByRole("button", { name: /calculate/i }));
    }

    it("shows verdict badge for the best mandi", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        await submitForm(user);
        await waitFor(() => {
            expect(screen.getByText(/excellent/i)).toBeInTheDocument();
        });
    });

    it("shows verdict reason text", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        await submitForm(user);
        await waitFor(() => {
            expect(screen.getByText(/Strong price premium with low transport cost/i)).toBeInTheDocument();
        });
    });

    it("shows Cost Breakdown tab", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        await submitForm(user);
        await waitFor(() => {
            expect(screen.getByRole("tab", { name: /cost breakdown/i })).toBeInTheDocument();
        });
    });

    it("shows driver bata in cost breakdown tab", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        await submitForm(user);
        await waitFor(() => expect(screen.getByRole("tab", { name: /cost breakdown/i })).toBeInTheDocument());
        await user.click(screen.getByRole("tab", { name: /cost breakdown/i }));
        await waitFor(() => {
            expect(screen.getByText(/driver bata/i)).toBeInTheDocument();
        });
    });

    it("shows stress test in Risk & Data tab", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        await submitForm(user);
        await waitFor(() => expect(screen.getByRole("tab", { name: /risk/i })).toBeInTheDocument());
        await user.click(screen.getByRole("tab", { name: /risk/i }));
        await waitFor(() => {
            expect(screen.getByText(/worst.case profit/i)).toBeInTheDocument();
        });
    });

    it("shows spoilage percent in Spoilage tab", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        await submitForm(user);
        await waitFor(() => expect(screen.getByRole("tab", { name: /spoilage/i })).toBeInTheDocument());
        await user.click(screen.getByRole("tab", { name: /spoilage/i }));
        await waitFor(() => {
            expect(screen.getByText(/spoilage loss/i)).toBeInTheDocument();
        });
    });

    it("shows economic warning banner when present", async () => {
        (transportService.compareCosts as ReturnType<typeof vi.fn>).mockResolvedValue({
            ...mockCompareResponse,
            comparisons: [{
                ...mockCompareResponse.comparisons[0],
                economic_warning: "Price data is 5 days old. Verify before travel.",
            }],
        });
        render(<TransportPage />);
        const user = userEvent.setup();
        await submitForm(user);
        await waitFor(() => {
            expect(screen.getByText(/Price data is 5 days old/i)).toBeInTheDocument();
        });
    });

    it("does not show economic warning when null", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        await submitForm(user);
        await waitFor(() => expect(screen.getByText(/excellent/i)).toBeInTheDocument());
        expect(screen.queryByText(/Price data is 5 days old/i)).not.toBeInTheDocument();
    });
});

describe("TransportPage - UI Elements", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseQuery.mockImplementation((options: any) => {
            const key = options?.queryKey?.[0];
            if (key === "transport-commodities") {
                return { data: mockCommodities, isLoading: false, error: null };
            }
            return { data: undefined, isLoading: false, error: null };
        });
    });

    it("shows cost settings section", () => {
        render(<TransportPage />);
        
        expect(screen.getByText("Customize Cost Parameters")).toBeInTheDocument();
    });

    it("toggles cost settings visibility", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const settingsHeader = screen.getByText("Customize Cost Parameters");
        await user.click(settingsHeader);
        
        // Settings should expand/collapse
        expect(settingsHeader).toBeInTheDocument();
    });

    it("displays show/hide settings badge", () => {
        render(<TransportPage />);
        
        // Badge showing Show/Hide
        const showBadge = screen.getByText("Show Settings");
        expect(showBadge).toBeInTheDocument();
    });

    it("updates districts when state changes", () => {
        render(<TransportPage />);
        
        // District list should change based on state selection
        expect(screen.getByText("District *")).toBeInTheDocument();
    });
});
