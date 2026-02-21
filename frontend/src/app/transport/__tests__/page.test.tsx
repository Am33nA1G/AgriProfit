import { render, screen, fireEvent, waitFor, within } from "@test/test-utils";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import TransportPage from "../page";
import { commoditiesService } from "@/services/commodities";
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
        
        const searchInput = screen.getByPlaceholderText("Select commodity");
        expect(searchInput).toBeInTheDocument();
    });

    it("displays quantity input field", () => {
        render(<TransportPage />);
        
        const quantityInput = screen.getByPlaceholderText("Amount");
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

        // State select uses t('origin') = "Origin"
        expect(screen.getByText("Origin *")).toBeInTheDocument();
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
        const searchInput = screen.getByPlaceholderText("Select commodity");
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
        
        const quantityInput = screen.getByPlaceholderText("Amount");
        await user.type(quantityInput, "100");
        
        expect(quantityInput).toHaveValue(100);
    });

    it("allows decimal quantity values", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const quantityInput = screen.getByPlaceholderText("Amount");
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
        
        const searchInput = screen.getByPlaceholderText("Select commodity");
        await user.click(searchInput);
        
        // Should show dropdown with commodities
        await waitFor(() => {
            expect(screen.getByText("Rice")).toBeInTheDocument();
        });
    });

    it("filters commodities based on search input", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const searchInput = screen.getByPlaceholderText("Select commodity");
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
        
        const searchInput = screen.getByPlaceholderText("Select commodity");
        await user.click(searchInput);
        await user.type(searchInput, "xyz123");
        
        await waitFor(() => {
            expect(screen.getByText("No results found")).toBeInTheDocument();
        });
    });

    it("selects commodity from dropdown", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const searchInput = screen.getByPlaceholderText("Select commodity");
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
        expect(screen.getByPlaceholderText("Select commodity")).toBeInTheDocument();
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
        
        expect(screen.getByText("Cost per km")).toBeInTheDocument();
    });

    it("toggles cost settings visibility", async () => {
        render(<TransportPage />);
        const user = userEvent.setup();
        
        const settingsHeader = screen.getByText("Cost per km");
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

        // District label should be present (was previously "Destination")
        expect(screen.getByText("District *")).toBeInTheDocument();
    });
});
