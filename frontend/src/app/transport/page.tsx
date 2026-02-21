"use client"

import { useState, useMemo } from "react"
import { useTranslations } from 'next-intl'
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
    }
    net_profit: number
    roi_percentage: number
    vehicle_type: string
    arrival_time: string
    trips: number
}

const VEHICLE_LABELS: Record<string, string> = {
    "TEMPO": "Tempo",
    "TRUCK_SMALL": "LCV",
    "TRUCK_LARGE": "HCV",
}

export default function TransportPage() {
    const t = useTranslations('transport')
    const tc = useTranslations('common')
    const [loading, setLoading] = useState(false)
    const [results, setResults] = useState<TransportResult[] | null>(null)
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
            tataAce: 18,       // Tata Ace / Mini Truck: ₹10-25/km range
            miniTruck: 22,     // Larger mini trucks
            lcv: 28,           // Eicher Pro / Tata 407: ₹15-40/km range
            truck: 32,         // Medium trucks
            tenWheeler: 42,    // 10-wheeler HCV
            multiAxle: 60      // Multi-axle heavy
        },
        loadingPerQuintal: 15,   // APMC hamali rates: ₹10-25/quintal avg
        loadingPerTrip: 0,       // Per-trip loading (optional, most charge per quintal)
        unloadingPerQuintal: 12, // Slightly lower than loading
        unloadingPerTrip: 0,     // Per-trip unloading (optional)
        driverAllowance: 800,    // Driver daily wage + food: ₹800-1200/day
        maintenance: 2,          // Vehicle wear & tear: ₹2-3/km
        weighbridge: 80,         // ₹50-100 range
        parking: 50,             // Mandi parking
        misc: 70,                // Documentation fees (bilty, permits, receipts)
        tollPerPlaza: { light: 110, medium: 200, heavy: 350 },  // NHAI 2025-26 rates
        tollPlazaSpacing: 60,    // NHAI standard ~60km between plazas
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
                    },
                    net_profit: Math.round(c.net_profit || 0),
                    roi_percentage: c.roi_percentage || 0,
                    vehicle_type: c.vehicle_type || "N/A",
                    arrival_time: arrivalTime,
                    trips: c.trips_required || 1,
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
                            {t('title')}
                        </h1>
                        <p className="text-muted-foreground">
                            {t('subtitle')}
                        </p>
                    </div>

                    {/* Input Form */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Truck className="h-5 w-5 text-orange-600" />
                                {t('title')}
                            </CardTitle>
                            <CardDescription>{t('subtitle')}</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                                {/* Searchable Commodity */}
                                <div className="relative">
                                    <Label>{tc('commodity')} *</Label>
                                    <div className="relative mt-1">
                                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                                        <Input
                                            placeholder={t('selectCommodity')}
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
                                                    <div className="px-3 py-2 text-sm text-muted-foreground">{tc('noResults')}</div>
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
                                    <Label>{tc('quantity')} *</Label>
                                    <div className="flex gap-2 mt-1">
                                        <Input
                                            type="number"
                                            placeholder={tc('amount')}
                                            value={form.quantity}
                                            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                                        />
                                        <Select value={form.unit} onValueChange={(v) => setForm({ ...form, unit: v })}>
                                            <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="kg">{tc('kg')}</SelectItem>
                                                <SelectItem value="quintal">{tc('quintal')}</SelectItem>
                                                <SelectItem value="ton">Ton</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                {/* Origin State */}
                                <div>
                                    <Label>{t('origin')} *</Label>
                                    <Select value={form.source_state} onValueChange={(v) => setForm({ ...form, source_state: v, source_district: "" })}>
                                        <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {statesList.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {/* District (within origin state) */}
                                <div>
                                    <Label>{t('district')} *</Label>
                                    <Select value={form.source_district} onValueChange={(v) => setForm({ ...form, source_district: v })}>
                                        <SelectTrigger className="mt-1"><SelectValue placeholder={t('selectDistrict')} /></SelectTrigger>
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
                                        {loading ? t('calculating') : t('calculate')}
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
                                <h3 className="text-lg font-semibold text-orange-700 mb-1">{t('noResults')}</h3>
                                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                                    No mandis with recent price data were found for <strong>{form.commodity}</strong> near <strong>{form.source_district}, {form.source_state}</strong>.
                                    Try a different commodity, district, or check if price data is available.
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {results && results.length > 0 && (
                        <>
                            {/* Best Option Analysis */}
                            {results[0].net_profit > 0 && (
                                <Card className="border-green-500 border-2 bg-green-50/50">
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2 text-green-700">
                                            <TrendingUp className="h-5 w-5" />
                                            {t('bestMandi')}: {results[0].mandi_name}
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                <div className="p-4 bg-white rounded-lg border">
                                                    <p className="text-sm text-muted-foreground mb-1">{t('netProfit')}</p>
                                                    <p className="text-2xl font-bold text-green-600">₹{results[0].net_profit.toLocaleString()}</p>
                                                    <p className="text-xs text-muted-foreground mt-1">
                                                        ₹{(results[0].net_profit / parseFloat(form.quantity || "1")).toFixed(0)} per {form.unit}
                                                    </p>
                                                </div>
                                                <div className="p-4 bg-white rounded-lg border">
                                                    <p className="text-sm text-muted-foreground mb-1">{t('recommendation')}</p>
                                                    <p className="text-2xl font-bold text-blue-600">{results[0].roi_percentage.toFixed(1)}%</p>
                                                    <p className="text-xs text-muted-foreground mt-1">Return on investment</p>
                                                </div>
                                                <div className="p-4 bg-white rounded-lg border">
                                                    <p className="text-sm text-muted-foreground mb-1">{t('distance')}</p>
                                                    <p className="text-2xl font-bold text-orange-600">{results[0].distance_km} km</p>
                                                    <p className="text-xs text-muted-foreground mt-1">Est. {results[0].arrival_time} travel time</p>
                                                </div>
                                            </div>
                                            
                                            <div className="p-4 bg-white rounded-lg border">
                                                <h4 className="font-semibold mb-2 text-sm">Analysis</h4>
                                                <ul className="space-y-2 text-sm text-muted-foreground">
                                                    <li className="flex items-start gap-2">
                                                        <span className="text-green-600 mt-0.5">✓</span>
                                                        <span><strong>Highest market price:</strong> ₹{(results[0].price_per_kg * 100).toFixed(2)}/quintal - 
                                                        {results[1] ? ` ₹${((results[0].price_per_kg - results[1].price_per_kg) * 100).toFixed(2)} more than 2nd best` : ' best price available'}</span>
                                                    </li>
                                                    <li className="flex items-start gap-2">
                                                        <span className="text-green-600 mt-0.5">✓</span>
                                                        <span><strong>Cost-effective distance:</strong> {results[0].distance_km} km balances transport costs (₹{results[0].costs.total.toLocaleString()}) with price advantage</span>
                                                    </li>
                                                    <li className="flex items-start gap-2">
                                                        <span className="text-green-600 mt-0.5">✓</span>
                                                        <span><strong>Optimal vehicle:</strong> {VEHICLE_LABELS[results[0].vehicle_type] || results[0].vehicle_type} ({results[0].trips} trip{results[0].trips > 1 ? 's' : ''}) minimizes freight costs</span>
                                                    </li>
                                                    <li className="flex items-start gap-2">
                                                        <span className="text-green-600 mt-0.5">✓</span>
                                                        <span><strong>Best profit margin:</strong> {results[0].gross_revenue > 0 ? ((results[0].net_profit / results[0].gross_revenue) * 100).toFixed(1) : "0.0"}% of gross revenue (₹{results[0].gross_revenue.toLocaleString()}) retained as profit</span>
                                                    </li>
                                                </ul>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center justify-between">
                                    <span>{t('results')}</span>
                                    <Badge variant="outline">{form.commodity} - {form.quantity} {form.unit}</Badge>
                                </CardTitle>
                                <CardDescription>All mandis ranked by profitability (highest profit first)</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="overflow-x-auto">
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>{tc('mandi')}</TableHead>
                                                <TableHead className="text-right">{t('distance')}</TableHead>
                                                <TableHead className="text-right">{tc('price')}/{tc('quintal')}</TableHead>
                                                <TableHead className="text-right">{t('totalCost')}</TableHead>
                                                <TableHead>{t('vehicleType')}</TableHead>
                                                <TableHead>{t('estimatedTime')}</TableHead>
                                                <TableHead className="text-right">ROI</TableHead>
                                                <TableHead className="text-right">{t('netProfit')}</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {results.map((r, i) => (
                                                <TableRow key={i} className={i === 0 ? "bg-green-50 border-l-4 border-l-green-500" : ""}>
                                                    <TableCell className="font-medium">
                                                        <div>{r.mandi_name}</div>
                                                        {r.district && <div className="text-xs text-muted-foreground">{r.district}, {r.state}</div>}
                                                        {i === 0 && <Badge className="mt-1 bg-green-600">{t('bestMandi')}</Badge>}
                                                    </TableCell>
                                                    <TableCell className="text-right">{r.distance_km} km</TableCell>
                                                    <TableCell className="text-right">₹{(r.price_per_kg * 100).toFixed(2)}</TableCell>
                                                    <TableCell className="text-right text-red-600">₹{r.costs.total.toLocaleString()}</TableCell>
                                                    <TableCell><Badge variant="outline">{VEHICLE_LABELS[r.vehicle_type] || r.vehicle_type}</Badge></TableCell>
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

                                {/* Cost Breakdown */}
                                {results.length > 0 && (
                                    <div className="mt-6 p-4 bg-muted/50 rounded-lg">
                                        <h4 className="font-semibold mb-3 flex items-center gap-2">
                                            <TrendingUp className="h-4 w-4" /> {t('totalCost')} ({t('bestMandi')}: {results[0].mandi_name})
                                        </h4>
                                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 text-sm">
                                            <div className="space-y-1">
                                                <p className="text-muted-foreground">{t('fuelCost')}</p>
                                                <p className="font-medium">₹{results[0].costs.freight.toLocaleString()}</p>
                                                <p className="text-xs text-muted-foreground">{VEHICLE_LABELS[results[0].vehicle_type] || results[0].vehicle_type} × {results[0].trips} trip(s)</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-muted-foreground">{t('tollCost')}</p>
                                                <p className="font-medium">₹{results[0].costs.toll.toLocaleString()}</p>
                                                <p className="text-xs text-muted-foreground">Highway tolls (both ways)</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-muted-foreground">{t('loadingCost')}</p>
                                                <p className="font-medium">₹{results[0].costs.loading.toLocaleString()}</p>
                                                <p className="text-xs text-muted-foreground">Hamali @₹15/quintal</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-muted-foreground">{t('unloadingCost')}</p>
                                                <p className="font-medium">₹{results[0].costs.unloading.toLocaleString()}</p>
                                                <p className="text-xs text-muted-foreground">Hamali @₹12/quintal</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-muted-foreground">Mandi Fee (1.5%)</p>
                                                <p className="font-medium">₹{results[0].costs.mandi_fee.toLocaleString()}</p>
                                                <p className="text-xs text-muted-foreground">Market fee</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-muted-foreground">Commission (2.5%)</p>
                                                <p className="font-medium">₹{results[0].costs.commission.toLocaleString()}</p>
                                                <p className="text-xs text-muted-foreground">Agent commission</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-muted-foreground">Additional Charges</p>
                                                <p className="font-medium">₹{results[0].costs.additional.toLocaleString()}</p>
                                                <p className="text-xs text-muted-foreground">Driver, Maintenance, Weighbridge, Parking, Docs</p>
                                            </div>
                                            <div className="space-y-1 col-span-2 md:col-span-3 lg:col-span-4 border-t pt-2 mt-2">
                                                <div className="flex justify-between items-center">
                                                    <p className="font-semibold">{t('totalCost')}</p>
                                                    <p className="font-bold text-red-600 text-lg">₹{results[0].costs.total.toLocaleString()}</p>
                                                </div>
                                                <div className="flex justify-between items-center text-xs text-muted-foreground mt-1">
                                                    <span>Includes freight, tolls, hamali, mandi fee (1.5%), commission (2.5%), driver, maintenance</span>
                                                    <span>ROI: {results[0].roi_percentage.toFixed(1)}%</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                        </>
                    )}

                    {/* Customizable Cost Settings */}
                    <Card>
                        <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => setShowCostSettings(!showCostSettings)}>
                            <CardTitle className="flex items-center justify-between text-base">
                                <span className="flex items-center gap-2"><Settings className="h-4 w-4" /> {t('costPerKm')}</span>
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
                                        <h4 className="font-semibold mb-3 text-sm">Labor Costs (Hamali - APMC notified rates)</h4>
                                        <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
                                            <div>
                                                <Label className="text-xs">Loading (₹ per quintal)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.loadingPerQuintal}
                                                    onChange={(e) => setCostSettings({ ...costSettings, loadingPerQuintal: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                                <p className="text-xs text-muted-foreground mt-0.5">Range: ₹10-25/quintal across India</p>
                                            </div>
                                            <div>
                                                <Label className="text-xs">Unloading (₹ per quintal)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.unloadingPerQuintal}
                                                    onChange={(e) => setCostSettings({ ...costSettings, unloadingPerQuintal: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                                <p className="text-xs text-muted-foreground mt-0.5">Range: ₹8-20/quintal across India</p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Driver & Maintenance */}
                                    <div>
                                        <h4 className="font-semibold mb-3 text-sm">Driver & Vehicle Maintenance</h4>
                                        <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
                                            <div>
                                                <Label className="text-xs">Driver Allowance (₹ per trip)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.driverAllowance}
                                                    onChange={(e) => setCostSettings({ ...costSettings, driverAllowance: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                                <p className="text-xs text-muted-foreground mt-0.5">Daily wage + food: ₹800-1200</p>
                                            </div>
                                            <div>
                                                <Label className="text-xs">Maintenance (₹ per km)</Label>
                                                <Input
                                                    type="number"
                                                    value={costSettings.maintenance}
                                                    onChange={(e) => setCostSettings({ ...costSettings, maintenance: parseFloat(e.target.value) || 0 })}
                                                    className="mt-1 h-8"
                                                />
                                                <p className="text-xs text-muted-foreground mt-0.5">Tyres, servicing, wear: ₹2-3/km</p>
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
                                                <Label className="text-xs">Miscellaneous (Bilty, Permits, Docs)</Label>
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
                                            loadingPerQuintal: 15, loadingPerTrip: 0, unloadingPerQuintal: 12, unloadingPerTrip: 0,
                                            driverAllowance: 800, maintenance: 2,
                                            weighbridge: 80, parking: 50, misc: 70,
                                            tollPerPlaza: { light: 110, medium: 200, heavy: 350 },
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
