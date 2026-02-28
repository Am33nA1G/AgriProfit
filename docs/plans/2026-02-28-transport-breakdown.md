# Transport Calculator Price Breakdown Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the backend logistics engine's rich output (verdict, stress test, spoilage, risk, full cost line items) into the transport calculator UI as a 4-tab best-mandi card.

**Architecture:** Two file changes only. `transport.ts` gets updated types. `page.tsx` gets an expanded mapping block + the existing best-mandi card replaced with a `<Tabs>` card. No new files, no new components, no backend changes.

**Tech Stack:** Next.js, React, shadcn/ui (`Tabs`, `Badge`, `Card`), Vitest + Testing Library

---

### Task 1: Update service types in `transport.ts`

**Files:**
- Modify: `frontend/src/services/transport.ts:1-70`

No tests needed — pure TypeScript interface changes caught by the compiler.

**Step 1: Replace the entire file with updated interfaces**

```ts
import api from '@/lib/api';

export interface StressTestResult {
    worst_case_profit: number;
    break_even_price_per_kg: number;
    margin_of_safety_pct: number;
    verdict_survives_stress: boolean;
}

export interface CostBreakdown {
    transport_cost: number;
    toll_cost: number;
    loading_cost: number;
    unloading_cost: number;
    mandi_fee: number;
    commission: number;
    additional_cost: number;
    total_cost: number;
    // New logistics engine fields
    driver_bata: number;
    cleaner_bata: number;
    halt_cost: number;
    breakdown_reserve: number;
    permit_cost: number;
    rto_buffer: number;
    loading_hamali: number;
    unloading_hamali: number;
}

export interface MandiComparison {
    mandi_id: string | null;
    mandi_name: string;
    state: string;
    district: string;
    distance_km: number;
    price_per_kg: number;
    gross_revenue: number;
    costs: CostBreakdown;
    net_profit: number;
    profit_per_kg: number;
    roi_percentage: number;
    vehicle_type: 'TEMPO' | 'TRUCK_SMALL' | 'TRUCK_LARGE';
    vehicle_capacity_kg: number;
    trips_required: number;
    recommendation: 'recommended' | 'not_recommended';
    // Verdict
    verdict: string;
    verdict_reason: string;
    // Route
    travel_time_hours: number;
    route_type: string;
    is_interstate: boolean;
    diesel_price_used: number;
    // Spoilage
    spoilage_percent: number;
    weight_loss_percent: number;
    grade_discount_percent: number;
    net_saleable_quantity_kg: number;
    // Price analytics
    price_volatility_7d: number;
    price_trend: string;
    // Risk
    risk_score: number;
    confidence_score: number;
    stability_class: string;
    stress_test: StressTestResult | null;
    economic_warning: string | null;
}

export interface TransportCompareResponse {
    commodity: string;
    quantity_kg: number;
    source_district: string;
    comparisons: MandiComparison[];
    best_mandi: MandiComparison | null;
    total_mandis_analyzed: number;
    distance_note: string | null;
}

export interface CompareRequest {
    commodity: string;
    quantity_kg: number;
    source_state: string;
    source_district: string;
    max_distance_km?: number;
    limit?: number;
}

export const transportService = {
    async compareCosts(data: CompareRequest): Promise<TransportCompareResponse> {
        const response = await api.post('/transport/compare', data);
        return response.data;
    },

    async getStates(): Promise<string[]> {
        const response = await api.get('/mandis/states');
        return response.data;
    },

    async getDistricts(state: string): Promise<string[]> {
        const response = await api.get('/mandis/districts', { params: { state } });
        return response.data;
    },

    async getVehicles(): Promise<Record<string, { capacity_kg: number; cost_per_km: number; description: string }>> {
        const response = await api.get('/transport/vehicles');
        return response.data?.vehicles || {};
    },
};
```

**Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors (or only pre-existing unrelated errors).

**Step 3: Commit**

```bash
git add frontend/src/services/transport.ts
git commit -m "feat(transport): update service types with full logistics engine fields"
```

---

### Task 2: Expand `TransportResult` interface and mapping block in `page.tsx`

**Files:**
- Modify: `frontend/src/app/transport/page.tsx:66-218`

**Step 1: Write a failing test that checks new fields are accessible after API response**

Add this describe block to `frontend/src/app/transport/__tests__/page.test.tsx`:

```tsx
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

// Add this describe block at the bottom of the file:
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
        const { transportService } = require("@/services/transport");
        transportService.compareCosts.mockResolvedValue(mockCompareResponse);
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
        const { transportService } = require("@/services/transport");
        transportService.compareCosts.mockResolvedValue({
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
```

**Step 2: Run tests to confirm they fail**

```bash
cd frontend && npx vitest run src/app/transport/__tests__/page.test.tsx 2>&1 | tail -20
```

Expected: 7 new tests FAIL (fields missing from TransportResult / tabs not rendered yet).

**Step 3: Expand `TransportResult` interface in `page.tsx`**

Find the `interface TransportResult {` block (line ~66) and replace it:

```ts
interface TransportResult {
    mandi_name: string
    state: string
    district: string
    distance_km: number
    price_per_kg: number
    gross_revenue: number
    costs: {
        freight: number
        toll: number
        loading: number
        unloading: number
        mandi_fee: number
        commission: number
        additional: number
        total: number
        driver_bata: number
        cleaner_bata: number
        halt_cost: number
        breakdown_reserve: number
        permit_cost: number
        rto_buffer: number
        loading_hamali: number
        unloading_hamali: number
    }
    net_profit: number
    roi_percentage: number
    vehicle_type: string
    vehicle_capacity_kg: number
    trips: number
    arrival_time: string
    verdict: string
    verdict_reason: string
    travel_time_hours: number
    route_type: string
    is_interstate: boolean
    diesel_price_used: number
    spoilage_percent: number
    weight_loss_percent: number
    grade_discount_percent: number
    net_saleable_quantity_kg: number
    price_volatility_7d: number
    price_trend: string
    risk_score: number
    confidence_score: number
    stability_class: string
    stress_test: {
        worst_case_profit: number
        break_even_price_per_kg: number
        margin_of_safety_pct: number
        verdict_survives_stress: boolean
    } | null
    economic_warning: string | null
}
```

**Step 4: Expand the mapping block**

Find the `const mapped: TransportResult[] = comparisons.map((c: any) => {` block and replace the entire map callback return value with:

```ts
return {
    mandi_name: c.mandi_name,
    state: c.state || "",
    district: c.district || "",
    distance_km: Math.round(distance),
    price_per_kg: c.price_per_kg || 0,
    gross_revenue: Math.round(c.gross_revenue || 0),
    costs: {
        freight: Math.round(c.costs?.transport_cost || 0),
        toll: Math.round(c.costs?.toll_cost || 0),
        loading: Math.round(c.costs?.loading_cost || 0),
        unloading: Math.round(c.costs?.unloading_cost || 0),
        mandi_fee: Math.round(c.costs?.mandi_fee || 0),
        commission: Math.round(c.costs?.commission || 0),
        additional: Math.round(c.costs?.additional_cost || 0),
        total: Math.round(c.costs?.total_cost || 0),
        driver_bata: Math.round(c.costs?.driver_bata || 0),
        cleaner_bata: Math.round(c.costs?.cleaner_bata || 0),
        halt_cost: Math.round(c.costs?.halt_cost || 0),
        breakdown_reserve: Math.round(c.costs?.breakdown_reserve || 0),
        permit_cost: Math.round(c.costs?.permit_cost || 0),
        rto_buffer: Math.round(c.costs?.rto_buffer || 0),
        loading_hamali: Math.round(c.costs?.loading_hamali || 0),
        unloading_hamali: Math.round(c.costs?.unloading_hamali || 0),
    },
    net_profit: Math.round(c.net_profit || 0),
    roi_percentage: c.roi_percentage || 0,
    vehicle_type: c.vehicle_type || "N/A",
    vehicle_capacity_kg: c.vehicle_capacity_kg || 0,
    trips: c.trips_required || 1,
    arrival_time: arrivalTime,
    verdict: c.verdict || "not_viable",
    verdict_reason: c.verdict_reason || "",
    travel_time_hours: c.travel_time_hours || 0,
    route_type: c.route_type || "mixed",
    is_interstate: c.is_interstate || false,
    diesel_price_used: c.diesel_price_used || 98.0,
    spoilage_percent: c.spoilage_percent || 0,
    weight_loss_percent: c.weight_loss_percent || 0,
    grade_discount_percent: c.grade_discount_percent || 0,
    net_saleable_quantity_kg: c.net_saleable_quantity_kg || 0,
    price_volatility_7d: c.price_volatility_7d || 0,
    price_trend: c.price_trend || "stable",
    risk_score: c.risk_score || 0,
    confidence_score: c.confidence_score ?? 100,
    stability_class: c.stability_class || "stable",
    stress_test: c.stress_test || null,
    economic_warning: c.economic_warning || null,
}
```

**Step 5: Commit (tests still failing — that's fine at this stage)**

```bash
git add frontend/src/app/transport/page.tsx
git commit -m "feat(transport): expand TransportResult with full logistics engine fields"
```

---

### Task 3: Replace best-mandi section with tabbed card

**Files:**
- Modify: `frontend/src/app/transport/page.tsx` — the best-mandi display block and the old cost breakdown card

**Step 1: Add Tabs to imports**

Find the import line that includes `Card, CardContent, ...` and add the Tabs import:

```ts
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
```

**Step 2: Add VERDICT_CONFIG helper above the component**

Add this constant near `VEHICLE_LABELS`:

```ts
const VERDICT_CONFIG: Record<string, { label: string; className: string }> = {
    excellent: { label: "Excellent", className: "bg-green-100 text-green-800 border-green-200" },
    good:      { label: "Good",      className: "bg-blue-100 text-blue-800 border-blue-200" },
    marginal:  { label: "Marginal",  className: "bg-amber-100 text-amber-800 border-amber-200" },
    not_viable:{ label: "Not Viable",className: "bg-red-100 text-red-800 border-red-200" },
}
```

**Step 3: Replace the entire best-mandi section**

Find the block starting with `{results[0].net_profit > 0 && (` and ending with the closing `)}` of the old "Detailed Cost Breakdown" card. Replace the entire thing with:

```tsx
{results[0].net_profit > 0 && (
    <Card className="border-green-200 bg-green-50/30">
        <CardHeader className="pb-2">
            <div className="flex items-center justify-between flex-wrap gap-2">
                <CardTitle className="text-lg">
                    {results[0].mandi_name}
                    <span className="ml-2 text-sm font-normal text-muted-foreground">
                        — Best Option
                    </span>
                </CardTitle>
                <Badge
                    variant="outline"
                    className={VERDICT_CONFIG[results[0].verdict]?.className ?? ""}
                >
                    {VERDICT_CONFIG[results[0].verdict]?.label ?? results[0].verdict}
                </Badge>
            </div>
        </CardHeader>
        <CardContent>
            {/* Economic warning */}
            {results[0].economic_warning && (
                <div className="mb-4 rounded-md bg-amber-50 border border-amber-200 px-4 py-2 text-sm text-amber-800">
                    ⚠ {results[0].economic_warning}
                </div>
            )}

            <Tabs defaultValue="overview">
                <TabsList className="mb-4">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="breakdown">Cost Breakdown</TabsTrigger>
                    <TabsTrigger value="risk">Risk &amp; Data</TabsTrigger>
                    <TabsTrigger value="spoilage">Spoilage</TabsTrigger>
                </TabsList>

                {/* ── Tab 1: Overview ── */}
                <TabsContent value="overview">
                    {/* Verdict reason */}
                    <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                        {results[0].verdict_reason}
                    </p>

                    {/* Stat chips */}
                    <div className="grid grid-cols-3 gap-3 mb-4">
                        <div className="rounded-lg border bg-background p-3 text-center">
                            <p className="text-xs text-muted-foreground">Net Profit</p>
                            <p className="text-xl font-bold text-green-600">₹{results[0].net_profit.toLocaleString()}</p>
                        </div>
                        <div className="rounded-lg border bg-background p-3 text-center">
                            <p className="text-xs text-muted-foreground">Per kg</p>
                            <p className="text-xl font-bold text-green-600">
                                ₹{(results[0].net_profit / parseFloat(form.quantity || "1")).toFixed(0)}
                            </p>
                        </div>
                        <div className="rounded-lg border bg-background p-3 text-center">
                            <p className="text-xs text-muted-foreground">ROI</p>
                            <p className="text-xl font-bold text-blue-600">{results[0].roi_percentage.toFixed(1)}%</p>
                        </div>
                    </div>

                    {/* Route line */}
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                        <span>{results[0].distance_km} km</span>
                        <span>·</span>
                        <span>{results[0].travel_time_hours.toFixed(1)}h round-trip</span>
                        <span>·</span>
                        <span>{VEHICLE_LABELS[results[0].vehicle_type] || results[0].vehicle_type}</span>
                        <span>·</span>
                        <span>{results[0].trips} trip{results[0].trips > 1 ? "s" : ""}</span>
                        {results[0].is_interstate && (
                            <Badge variant="outline" className="text-xs">Interstate</Badge>
                        )}
                    </div>
                </TabsContent>

                {/* ── Tab 2: Cost Breakdown ── */}
                <TabsContent value="breakdown">
                    <div className="space-y-1 text-sm">
                        {/* Revenue rows */}
                        <div className="flex justify-between py-1">
                            <span className="text-muted-foreground">Gross Revenue</span>
                            <span className="font-medium">₹{results[0].gross_revenue.toLocaleString()}</span>
                        </div>
                        {(results[0].spoilage_percent + results[0].grade_discount_percent) > 0 && (
                            <div className="flex justify-between py-1 text-amber-700">
                                <span>− Spoilage &amp; Grade Loss</span>
                                <span>
                                    −₹{Math.round(
                                        results[0].gross_revenue *
                                        (results[0].spoilage_percent + results[0].grade_discount_percent) / 100
                                    ).toLocaleString()}
                                </span>
                            </div>
                        )}
                        <div className="flex justify-between py-1 border-b mb-1">
                            <span className="text-muted-foreground">Adjusted Revenue</span>
                            <span className="font-medium">
                                ₹{Math.round(
                                    results[0].gross_revenue *
                                    (1 - (results[0].spoilage_percent + results[0].grade_discount_percent) / 100)
                                ).toLocaleString()}
                            </span>
                        </div>

                        {/* Deduction rows — hide zero values */}
                        {[
                            { label: "Freight", value: results[0].costs.freight },
                            { label: "Toll", value: results[0].costs.toll },
                            { label: "Driver Bata", value: results[0].costs.driver_bata },
                            { label: "Cleaner Bata", value: results[0].costs.cleaner_bata },
                            { label: "Night Halt", value: results[0].costs.halt_cost },
                            { label: "Breakdown Reserve", value: results[0].costs.breakdown_reserve },
                            { label: "Interstate Permit", value: results[0].costs.permit_cost },
                            { label: "RTO Buffer", value: results[0].costs.rto_buffer },
                            { label: "Loading Hamali", value: results[0].costs.loading_hamali },
                            { label: "Unloading Hamali", value: results[0].costs.unloading_hamali },
                            { label: "Mandi Fee (1.5%)", value: results[0].costs.mandi_fee },
                            { label: "Commission (2.5%)", value: results[0].costs.commission },
                            { label: "Misc (weighbridge etc.)", value: results[0].costs.additional },
                        ]
                            .filter(({ value }) => value > 0)
                            .map(({ label, value }) => (
                                <div key={label} className="flex justify-between py-1 text-red-700">
                                    <span>− {label}</span>
                                    <span>−₹{value.toLocaleString()}</span>
                                </div>
                            ))}

                        {/* Net profit */}
                        <div className="flex justify-between py-2 border-t mt-1 font-bold">
                            <span>Net Profit</span>
                            <span className={results[0].net_profit >= 0 ? "text-green-600" : "text-red-600"}>
                                ₹{results[0].net_profit.toLocaleString()}
                            </span>
                        </div>
                    </div>
                </TabsContent>

                {/* ── Tab 3: Risk & Data ── */}
                <TabsContent value="risk">
                    <div className="space-y-4 text-sm">
                        {/* Confidence */}
                        <div>
                            <div className="flex justify-between mb-1">
                                <span className="text-muted-foreground">Data Confidence</span>
                                <span className="font-medium">{results[0].confidence_score}/100</span>
                            </div>
                            <div className="h-2 rounded-full bg-muted overflow-hidden">
                                <div
                                    className="h-full bg-blue-500 rounded-full"
                                    style={{ width: `${results[0].confidence_score}%` }}
                                />
                            </div>
                        </div>

                        {/* Price trend + volatility */}
                        <div className="flex items-center gap-3">
                            <span className="text-muted-foreground">Price Trend</span>
                            <Badge variant="outline" className={
                                results[0].price_trend === "rising"  ? "text-green-700 border-green-300" :
                                results[0].price_trend === "falling" ? "text-red-700 border-red-300" :
                                "text-muted-foreground"
                            }>
                                {results[0].price_trend === "rising"  ? "Rising ↑" :
                                 results[0].price_trend === "falling" ? "Falling ↓" : "Stable →"}
                            </Badge>
                            <span className="text-muted-foreground">
                                {results[0].price_volatility_7d.toFixed(1)}% 7-day volatility
                            </span>
                        </div>

                        {/* Stability class */}
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground">Stability</span>
                            <Badge variant="outline" className={
                                results[0].stability_class === "stable"   ? "text-green-700" :
                                results[0].stability_class === "moderate" ? "text-amber-700" :
                                "text-red-700"
                            }>
                                {results[0].stability_class.charAt(0).toUpperCase() + results[0].stability_class.slice(1)}
                            </Badge>
                        </div>

                        {/* Stress test */}
                        {results[0].stress_test && (
                            <div className="rounded-md bg-muted/60 border p-3 space-y-2">
                                <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
                                    Stress Test (diesel+15%, toll+25%, price−12%, spoilage+5pp)
                                </p>
                                <div className="grid grid-cols-2 gap-2">
                                    <div>
                                        <p className="text-xs text-muted-foreground">Worst-Case Profit</p>
                                        <p className={`font-semibold ${results[0].stress_test.worst_case_profit >= 0 ? "text-green-600" : "text-red-600"}`}>
                                            ₹{Math.round(results[0].stress_test.worst_case_profit).toLocaleString()}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground">Break-Even Price</p>
                                        <p className="font-semibold">₹{results[0].stress_test.break_even_price_per_kg.toFixed(2)}/kg</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground">Margin of Safety</p>
                                        <p className="font-semibold">{results[0].stress_test.margin_of_safety_pct.toFixed(1)}%</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground">Survives Stress</p>
                                        <p className={`font-semibold ${results[0].stress_test.verdict_survives_stress ? "text-green-600" : "text-red-600"}`}>
                                            {results[0].stress_test.verdict_survives_stress ? "✓ Pass" : "✗ Fail"}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </TabsContent>

                {/* ── Tab 4: Spoilage ── */}
                <TabsContent value="spoilage">
                    <div className="space-y-3 text-sm">
                        {[
                            { label: "Spoilage Loss", value: `${results[0].spoilage_percent.toFixed(1)}%` },
                            { label: "Weight Shrinkage", value: `${results[0].weight_loss_percent.toFixed(1)}%` },
                            { label: "Grade Discount", value: `${results[0].grade_discount_percent.toFixed(1)}%` },
                        ].map(({ label, value }) => (
                            <div key={label} className="flex justify-between py-1 border-b">
                                <span className="text-muted-foreground">{label}</span>
                                <span className="font-medium text-amber-700">{value}</span>
                            </div>
                        ))}
                        <div className="flex justify-between py-1">
                            <span className="text-muted-foreground">Net Saleable Quantity</span>
                            <span className="font-medium">
                                {Math.round(results[0].net_saleable_quantity_kg).toLocaleString()} kg
                                <span className="text-muted-foreground"> of {parseFloat(form.quantity || "0").toLocaleString()} kg</span>
                            </span>
                        </div>
                        <p className="text-xs text-muted-foreground pt-2">
                            Diesel used in calculation: ₹{results[0].diesel_price_used}/L
                        </p>
                    </div>
                </TabsContent>
            </Tabs>
        </CardContent>
    </Card>
)}
```

**Step 4: Run the failing tests — most should now pass**

```bash
cd frontend && npx vitest run src/app/transport/__tests__/page.test.tsx 2>&1 | tail -20
```

Expected: all 7 new tests PASS. Fix any failures before continuing.

**Step 5: Commit**

```bash
git add frontend/src/app/transport/page.tsx
git commit -m "feat(transport): replace best-mandi card with 4-tab breakdown layout"
```

---

### Task 4: Add verdict badge column to comparison table

**Files:**
- Modify: `frontend/src/app/transport/page.tsx` — the comparison table

**Step 1: Write failing test**

Add to the `describe("TransportPage - Results Display")` block in the test file:

```tsx
it("shows verdict badge in comparison table row", async () => {
    render(<TransportPage />);
    const user = userEvent.setup();
    await submitForm(user);
    await waitFor(() => {
        // The table should have the verdict badge (text "Excellent") — it appears once in the card header too
        const badges = screen.getAllByText(/excellent/i);
        expect(badges.length).toBeGreaterThanOrEqual(1);
    });
});
```

**Step 2: Run to confirm it fails**

```bash
cd frontend && npx vitest run src/app/transport/__tests__/page.test.tsx -t "verdict badge in comparison table" 2>&1 | tail -10
```

**Step 3: Add Verdict column to table**

Find the `<TableHeader>` row in the comparison table and add a header:

```tsx
<TableHead>Verdict</TableHead>
```

Add it between the `Vehicle` and `ROI` headers.

Find the corresponding `<TableRow>` render for each result `r` and add the cell in the same position:

```tsx
<TableCell>
    <Badge
        variant="outline"
        className={`text-xs ${VERDICT_CONFIG[r.verdict]?.className ?? ""}`}
    >
        {VERDICT_CONFIG[r.verdict]?.label ?? r.verdict}
    </Badge>
</TableCell>
```

**Step 4: Run all transport tests**

```bash
cd frontend && npx vitest run src/app/transport/__tests__/page.test.tsx 2>&1 | tail -10
```

Expected: all tests PASS.

**Step 5: Commit**

```bash
git add frontend/src/app/transport/page.tsx frontend/src/app/transport/__tests__/page.test.tsx
git commit -m "feat(transport): add verdict badge to comparison table"
```

---

### Task 5: Full test run and cleanup

**Step 1: Run full frontend test suite**

```bash
cd frontend && npx vitest run 2>&1 | tail -15
```

Expected: all previously passing tests still pass. Fix any regressions.

**Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -v "node_modules" | head -20
```

Expected: no new errors.

**Step 3: Final commit if any cleanup was needed**

```bash
git add -p
git commit -m "fix(transport): resolve any post-refactor test/type issues"
```
