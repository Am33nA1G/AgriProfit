"use client"

import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import {
    Truck,
    TrendingUp,
    Loader2,
    Search,
    Settings
} from "lucide-react"
import { toast } from "sonner"
import { AppLayout } from "@/components/layout/AppLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { commoditiesService } from "@/services/commodities"
import { transportService } from "@/services/transport"

const COMMODITIES = ["Wheat", "Rice", "Tomato", "Potato", "Onion", "Banana", "Coconut", "Pepper", "Cardamom", "Rubber"]

const INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]


const STATE_DISTRICTS: Record<string, string[]> = {
    "Kerala": ["Thiruvananthapuram", "Kollam", "Alappuzha", "Kottayam", "Idukki", "Ernakulam", "Thrissur", "Palakkad", "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod"],
    "Tamil Nadu": ["Chennai", "Chengalpattu", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Erode", "Vellore", "Thoothukudi", "Thanjavur", "Dindigul", "Krishnagiri", "Kancheepuram", "Tiruvannamalai", "Cuddalore", "Villupuram", "Nagapattinam", "Tiruppur", "Namakkal", "Karur", "Dharmapuri", "Nilgiris", "Kanyakumari"],
    "Karnataka": ["Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Mangaluru", "Hubli-Dharwad", "Belagavi", "Tumakuru", "Davangere", "Ballari", "Shivamogga", "Kalaburagi", "Hassan"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool", "Kadapa", "Tirupati", "Anantapur", "Rajahmundry", "Kakinada", "Eluru", "Ongole"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam", "Ramagundam", "Mahbubnagar", "Nalgonda", "Adilabad", "Suryapet", "Siddipet", "Medak"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur", "Kolhapur", "Thane", "Satara", "Sangli", "Ahmednagar", "Jalgaon", "Amravati"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Junagadh", "Gandhinagar", "Anand", "Mehsana", "Bharuch", "Morbi", "Kutch"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar", "Satna", "Rewa", "Ratlam", "Chhindwara", "Dewas", "Khandwa", "Vidisha"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Bikaner", "Ajmer", "Bharatpur", "Alwar", "Sikar", "Pali", "Bhilwara", "Nagaur", "Chittorgarh"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra", "Varanasi", "Meerut", "Allahabad", "Bareilly", "Aligarh", "Moradabad", "Ghaziabad", "Noida", "Gorakhpur", "Mathura"],
    "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga", "Purnia", "Arrah", "Begusarai", "Katihar", "Munger", "Chhapra", "Samastipur"],
    "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol", "Bardhaman", "Malda", "Kharagpur", "Haldia", "Baharampur", "Raiganj", "Krishnanagar"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur", "Puri", "Balasore", "Bhadrak", "Baripada", "Jharsuguda", "Koraput", "Angul"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Mohali", "Pathankot", "Hoshiarpur", "Moga", "Firozpur", "Kapurthala", "Sangrur"],
    "Haryana": ["Gurugram", "Faridabad", "Panipat", "Ambala", "Yamunanagar", "Rohtak", "Hisar", "Karnal", "Sonipat", "Panchkula", "Bhiwani", "Sirsa"],
    "Goa": ["North Goa", "South Goa"],
    "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur", "Korba", "Durg", "Rajnandgaon", "Jagdalpur", "Raigarh", "Ambikapur", "Dhamtari"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Hazaribagh", "Deoghar", "Giridih", "Ramgarh", "Dumka", "Chaibasa"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Rishikesh", "Haldwani", "Roorkee", "Kashipur", "Rudrapur", "Nainital", "Almora", "Pithoragarh"],
    "Himachal Pradesh": ["Shimla", "Dharamshala", "Mandi", "Solan", "Kullu", "Bilaspur", "Hamirpur", "Una", "Kangra", "Palampur"],
    "Assam": ["Guwahati", "Silchar", "Dibrugarh", "Jorhat", "Nagaon", "Tinsukia", "Tezpur", "Bongaigaon", "Karimganj", "Sivasagar"],
    "Arunachal Pradesh": ["Itanagar", "Naharlagun", "Pasighat", "Tawang", "Ziro", "Bomdila", "Along", "Tezu", "Roing", "Changlang"],
    "Manipur": ["Imphal East", "Imphal West", "Thoubal", "Bishnupur", "Churachandpur", "Senapati", "Ukhrul", "Chandel"],
    "Meghalaya": ["Shillong", "Tura", "Jowai", "Nongstoin", "Williamnagar", "Baghmara", "Resubelpara"],
    "Mizoram": ["Aizawl", "Lunglei", "Champhai", "Serchhip", "Kolasib", "Lawngtlai", "Mamit", "Saiha"],
    "Nagaland": ["Kohima", "Dimapur", "Mokokchung", "Tuensang", "Wokha", "Zunheboto", "Mon", "Phek"],
    "Tripura": ["Agartala", "Udaipur", "Dharmanagar", "Kailashahar", "Khowai", "Ambassa", "Belonia", "Sabroom"],
    "Sikkim": ["Gangtok", "Namchi", "Gyalshing", "Mangan", "Rangpo", "Singtam", "Jorethang"],
}


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

const VEHICLE_LABELS: Record<string, string> = {
    "TEMPO": "Tempo",
    "TRUCK_SMALL": "LCV",
    "TRUCK_LARGE": "HCV",
}

const VERDICT_CONFIG: Record<string, { label: string; className: string }> = {
    excellent: { label: "Excellent", className: "bg-green-100 text-green-800 border-green-200" },
    good:      { label: "Good",      className: "bg-blue-100 text-blue-800 border-blue-200" },
    marginal:  { label: "Marginal",  className: "bg-amber-100 text-amber-800 border-amber-200" },
    not_viable:{ label: "Not Viable",className: "bg-red-100 text-red-800 border-red-200" },
}

export default function TransportPage() {
    const [loading, setLoading] = useState(false)
    const [results, setResults] = useState<TransportResult[] | null>(null)
    const [activeTab, setActiveTab] = useState("overview")
    const [commoditySearch, setCommoditySearch] = useState("")
    const [isCommodityDropdownOpen, setIsCommodityDropdownOpen] = useState(false)
    const [showCostSettings, setShowCostSettings] = useState(false)

    const [form, setForm] = useState({
        commodity: "",
        quantity: "",
        unit: "kg",
        source_state: "Kerala",
        source_district: ""
    })

    const [costSettings, setCostSettings] = useState({
        freightRates: {
            tataAce: 18,  // Updated for 2026 diesel prices
            miniTruck: 22,
            lcv: 28,
            truck: 32,
            tenWheeler: 42,
            multiAxle: 60
        },
        loadingPerQuintal: 3.5,  // Realistic hamali rates
        loadingPerTrip: 120,
        unloadingPerQuintal: 3.0,
        unloadingPerTrip: 100,
        weighbridge: 80,
        parking: 50,
        misc: 70,  // Documentation fees
        tollPerPlaza: { light: 110, medium: 210, heavy: 360 },  // 2026 NHAI rates
        tollPlazaSpacing: 60,
    })

    const { data: allCommodities } = useQuery({
        queryKey: ["transport-commodities"],
        queryFn: () => commoditiesService.getAll({ limit: 500 }),
        staleTime: 300000,
    })

    // Fetch real states from API, fall back to hardcoded list
    const { data: apiStates } = useQuery({
        queryKey: ["transport-states"],
        queryFn: () => transportService.getStates(),
        staleTime: 300000,
    })
    const statesList = apiStates && apiStates.length > 0 ? apiStates : INDIAN_STATES

    // Fetch real districts from API for selected state, fall back to hardcoded
    const { data: apiDistricts } = useQuery({
        queryKey: ["transport-districts", form.source_state],
        queryFn: () => transportService.getDistricts(form.source_state),
        staleTime: 300000,
        enabled: !!form.source_state,
    })

    const commodityNames = useMemo(() => allCommodities?.map((c: any) => c.name) || COMMODITIES, [allCommodities])
    const filteredCommodities = useMemo(() => {
        if (!commoditySearch) return commodityNames
        return commodityNames.filter((c: string) => c.toLowerCase().includes(commoditySearch.toLowerCase()))
    }, [commodityNames, commoditySearch])

    const currentDistricts = apiDistricts && apiDistricts.length > 0
        ? apiDistricts
        : STATE_DISTRICTS[form.source_state] || []

    const handleCalculate = async () => {
        if (!form.commodity || !form.quantity || !form.source_district) {
            toast.error("Please fill all required fields")
            return
        }

        setLoading(true)
        const qty = parseFloat(form.quantity) * (form.unit === "ton" ? 1000 : form.unit === "quintal" ? 100 : 1)

        try {
            const response = await transportService.compareCosts({
                commodity: form.commodity,
                quantity_kg: qty,
                source_state: form.source_state,
                source_district: form.source_district,
            })

            // Map backend response to the UI format
            const comparisons = response.comparisons || []
            const mapped: TransportResult[] = comparisons.map((c: any) => {
                const distance = c.distance_km || 0
                const minHours = Math.ceil(distance / 50)
                const maxHours = Math.ceil(distance / 35)
                const arrivalTime = distance === 0 ? "N/A" :
                    minHours === maxHours ? `~${minHours} hr${minHours > 1 ? 's' : ''}` : `${minHours}-${maxHours} hrs`

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
            })

            if (mapped.length === 0) {
                toast.warning("No mandis found with price data for this commodity and location")
            }

            setResults(mapped.sort((a, b) => b.net_profit - a.net_profit))
        } catch (error: any) {
            console.error("Transport comparison failed:", error)
            toast.error(error?.response?.data?.detail || "Failed to calculate transport costs. Please try again.")
            setResults(null)
        } finally {
            setLoading(false)
        }
    }

    return (
        <AppLayout>
            <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8">
                <div className="max-w-7xl mx-auto space-y-6">
                    <div className="space-y-2">
                        <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
                            <Truck className="h-8 w-8 text-primary" />
                            Transport Cost Calculator
                        </h1>
                        <p className="text-muted-foreground">
                            Calculate transport costs and find the most profitable mandi for your produce
                        </p>
                    </div>

                    {/* Input Form */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Truck className="h-5 w-5 text-orange-600" />
                                Transport Cost Calculator
                            </CardTitle>
                            <CardDescription>Calculate transport costs and find the most profitable mandi for your produce</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                                {/* Searchable Commodity */}
                                <div className="relative">
                                    <Label>Commodity *</Label>
                                    <div className="relative mt-1">
                                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                                        <Input
                                            placeholder="Search commodity..."
                                            value={form.commodity || commoditySearch}
                                            onChange={(e) => {
                                                setCommoditySearch(e.target.value)
                                                setForm({ ...form, commodity: "" })
                                            }}
                                            onFocus={() => setIsCommodityDropdownOpen(true)}
                                            className="pl-10"
                                        />
                                    </div>
                                    {isCommodityDropdownOpen && (
                                        <>
                                            <div className="fixed inset-0 z-40" onClick={() => setIsCommodityDropdownOpen(false)} />
                                            <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-md shadow-md max-h-52 overflow-y-auto">
                                                {filteredCommodities.length === 0 ? (
                                                    <div className="px-3 py-2 text-sm text-muted-foreground">No commodities found</div>
                                                ) : (
                                                    filteredCommodities.map((c: string) => (
                                                        <div
                                                            key={c}
                                                            className={`relative flex cursor-pointer select-none items-center rounded-sm px-3 py-2 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground ${form.commodity === c ? "bg-accent text-accent-foreground font-medium" : ""}`}
                                                            onClick={() => {
                                                                setForm({ ...form, commodity: c })
                                                                setCommoditySearch("")
                                                                setIsCommodityDropdownOpen(false)
                                                            }}
                                                        >
                                                            {c}
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        </>
                                    )}
                                </div>

                                {/* Quantity */}
                                <div>
                                    <Label>Quantity *</Label>
                                    <div className="flex gap-2 mt-1">
                                        <Input
                                            type="number"
                                            placeholder="Enter amount"
                                            value={form.quantity}
                                            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                                        />
                                        <Select value={form.unit} onValueChange={(v) => setForm({ ...form, unit: v })}>
                                            <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="kg">kg</SelectItem>
                                                <SelectItem value="quintal">Quintal</SelectItem>
                                                <SelectItem value="ton">Ton</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                {/* State */}
                                <div>
                                    <Label>State</Label>
                                    <Select value={form.source_state} onValueChange={(v) => setForm({ ...form, source_state: v, source_district: "" })}>
                                        <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {statesList.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {/* District */}
                                <div>
                                    <Label>District *</Label>
                                    <Select value={form.source_district} onValueChange={(v) => setForm({ ...form, source_district: v })}>
                                        <SelectTrigger className="mt-1"><SelectValue placeholder="Select district" /></SelectTrigger>
                                        <SelectContent>
                                            {currentDistricts.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {/* Calculate Button */}
                                <div>
                                    <Label>&nbsp;</Label>
                                    <Button onClick={handleCalculate} disabled={loading} className="w-full mt-1 bg-orange-600 hover:bg-orange-700">
                                        {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Truck className="h-4 w-4 mr-2" />}
                                        Calculate
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Results */}
                    {results && results.length === 0 && (
                        <Card className="border-orange-300 bg-orange-50/50">
                            <CardContent className="py-8 text-center">
                                <Truck className="h-12 w-12 mx-auto text-orange-400 mb-3" />
                                <h3 className="text-lg font-semibold text-orange-700 mb-1">No Mandis Found</h3>
                                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                                    No mandis with recent price data were found for <strong>{form.commodity}</strong> near <strong>{form.source_district}, {form.source_state}</strong>.
                                    Try a different commodity, district, or check if price data is available.
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {results && results.length > 0 && (
                        <>
                            {/* Best Option Analysis — tabbed card */}
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

                                        <Tabs value={activeTab} onValueChange={setActiveTab}>
                                            <TabsList className="mb-4">
                                                <TabsTrigger value="overview" role="tab">Overview</TabsTrigger>
                                                <TabsTrigger value="breakdown" role="tab">Cost Breakdown</TabsTrigger>
                                                <TabsTrigger value="risk" role="tab">Risk &amp; Data</TabsTrigger>
                                                <TabsTrigger value="spoilage" role="tab">Spoilage</TabsTrigger>
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

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center justify-between">
                                    <span>Transport Comparison Results</span>
                                    <Badge variant="outline">{form.commodity} - {form.quantity} {form.unit}</Badge>
                                </CardTitle>
                                <CardDescription>All mandis ranked by profitability (highest profit first)</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="overflow-x-auto">
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Mandi</TableHead>
                                                <TableHead className="text-right">Distance</TableHead>
                                                <TableHead className="text-right">Price/quintal</TableHead>
                                                <TableHead className="text-right">Transport Cost</TableHead>
                                                <TableHead>Vehicle</TableHead>
                                                <TableHead>Verdict</TableHead>
                                                <TableHead>Est. Time</TableHead>
                                                <TableHead className="text-right">ROI</TableHead>
                                                <TableHead className="text-right">Net Profit</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {results.map((r, i) => (
                                                <TableRow key={i} className={i === 0 ? "bg-green-50 border-l-4 border-l-green-500" : ""}>
                                                    <TableCell className="font-medium">
                                                        <div>{r.mandi_name}</div>
                                                        {r.district && <div className="text-xs text-muted-foreground">{r.district}, {r.state}</div>}
                                                        {i === 0 && <Badge className="mt-1 bg-green-600">Best Option</Badge>}
                                                    </TableCell>
                                                    <TableCell className="text-right">{r.distance_km} km</TableCell>
                                                    <TableCell className="text-right">₹{(r.price_per_kg * 100).toFixed(2)}</TableCell>
                                                    <TableCell className="text-right text-red-600">₹{r.costs.total.toLocaleString()}</TableCell>
                                                    <TableCell><Badge variant="outline">{VEHICLE_LABELS[r.vehicle_type] || r.vehicle_type}</Badge></TableCell>
                                                    <TableCell>
                                                        <Badge
                                                            variant="outline"
                                                            className={`text-xs ${VERDICT_CONFIG[r.verdict]?.className ?? ""}`}
                                                        >
                                                            {VERDICT_CONFIG[r.verdict]?.label ?? r.verdict}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell className="text-muted-foreground">{r.arrival_time}</TableCell>
                                                    <TableCell className="text-right">
                                                        <Badge variant={r.roi_percentage > 500 ? "default" : r.roi_percentage > 300 ? "secondary" : "outline"}>
                                                            {r.roi_percentage.toFixed(1)}%
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell className="text-right font-semibold text-green-600">₹{r.net_profit.toLocaleString()}</TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>

                            </CardContent>
                        </Card>
                        </>
                    )}

                    {/* Customizable Cost Settings */}
                    <Card>
                        <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => setShowCostSettings(!showCostSettings)}>
                            <CardTitle className="flex items-center justify-between text-base">
                                <span className="flex items-center gap-2"><Settings className="h-4 w-4" /> Customize Cost Parameters</span>
                                <Badge variant="outline" className="font-normal">{showCostSettings ? "Hide" : "Show"} Settings</Badge>
                            </CardTitle>
                            <p className="text-sm text-muted-foreground mt-1">
                                Adjust freight rates, toll charges, and labor costs based on your local rates. Default values reflect February 2026 Indian market rates.
                            </p>
                        </CardHeader>

                        {showCostSettings && (
                            <CardContent className="border-t">
                                <div className="space-y-6">
                                    {/* Freight Rates */}
                                    <div>
                                        <h4 className="font-semibold mb-3 text-sm">Freight Rates (₹ per km)</h4>
                                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                            {Object.entries(costSettings.freightRates).map(([key, value]) => (
                                                <div key={key}>
                                                    <Label className="text-xs">{key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}</Label>
                                                    <Input
                                                        type="number"
                                                        value={value}
                                                        onChange={(e) => setCostSettings({ ...costSettings, freightRates: { ...costSettings.freightRates, [key]: parseFloat(e.target.value) || 0 } })}
                                                        className="mt-1 h-8"
                                                    />
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Toll Charges */}
                                    <div>
                                        <h4 className="font-semibold mb-3 text-sm">Toll Charges (₹ per plaza)</h4>
                                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                            <div>
                                                <Label className="text-xs">Light Vehicle (Tata Ace, Mini Truck)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.tollPerPlaza.light}
                                                    onChange={(e) => setCostSettings({ ...costSettings, tollPerPlaza: { ...costSettings.tollPerPlaza, light: parseFloat(e.target.value) || 0 } })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Medium Vehicle (LCV, Truck)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.tollPerPlaza.medium}
                                                    onChange={(e) => setCostSettings({ ...costSettings, tollPerPlaza: { ...costSettings.tollPerPlaza, medium: parseFloat(e.target.value) || 0 } })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Heavy Vehicle (10-Wheeler, Multi-Axle)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.tollPerPlaza.heavy}
                                                    onChange={(e) => setCostSettings({ ...costSettings, tollPerPlaza: { ...costSettings.tollPerPlaza, heavy: parseFloat(e.target.value) || 0 } })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Toll Plaza Spacing (km)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.tollPlazaSpacing}
                                                    onChange={(e) => setCostSettings({ ...costSettings, tollPlazaSpacing: parseFloat(e.target.value) || 60 })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Labor Costs */}
                                    <div>
                                        <h4 className="font-semibold mb-3 text-sm">Labor Costs (Hamali)</h4>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                            <div>
                                                <Label className="text-xs">Loading (₹ per quintal)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.loadingPerQuintal}
                                                    onChange={(e) => setCostSettings({ ...costSettings, loadingPerQuintal: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Loading (₹ per trip)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.loadingPerTrip}
                                                    onChange={(e) => setCostSettings({ ...costSettings, loadingPerTrip: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Unloading (₹ per quintal)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.unloadingPerQuintal}
                                                    onChange={(e) => setCostSettings({ ...costSettings, unloadingPerQuintal: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Unloading (₹ per trip)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.unloadingPerTrip}
                                                    onChange={(e) => setCostSettings({ ...costSettings, unloadingPerTrip: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Additional Charges */}
                                    <div>
                                        <h4 className="font-semibold mb-3 text-sm">Additional Charges (₹ per trip)</h4>
                                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                            <div>
                                                <Label className="text-xs">Weighbridge Fee</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.weighbridge}
                                                    onChange={(e) => setCostSettings({ ...costSettings, weighbridge: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Parking Charges</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.parking}
                                                    onChange={(e) => setCostSettings({ ...costSettings, parking: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Miscellaneous (Documentation, etc.)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.misc}
                                                    onChange={(e) => setCostSettings({ ...costSettings, misc: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Reset Button */}
                                    <div className="flex justify-end pt-2 border-t">
                                        <Button variant="outline" size="sm" onClick={() => setCostSettings({
                                            freightRates: { tataAce: 18, miniTruck: 22, lcv: 28, truck: 32, tenWheeler: 42, multiAxle: 60 },
                                            loadingPerQuintal: 3.5, loadingPerTrip: 120, unloadingPerQuintal: 3.0, unloadingPerTrip: 100,
                                            weighbridge: 80, parking: 50, misc: 70,
                                            tollPerPlaza: { light: 110, medium: 210, heavy: 360 },
                                            tollPlazaSpacing: 60,
                                        })}>Reset to Default Rates (2026)</Button>
                                    </div>
                                </div>
                            </CardContent>
                        )}
                    </Card>
                </div>
            </div>
        </AppLayout>
    )
}
