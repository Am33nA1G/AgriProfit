"use client"

import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import {
    CalendarDays,
    Loader2,
    Search,
    TrendingUp,
    TrendingDown,
    AlertTriangle,
    Info,
} from "lucide-react"
import { AppLayout } from "@/components/layout/AppLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    ComposedChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ErrorBar, Cell, Legend,
} from "recharts"
import api from "@/lib/api"

interface MonthlyStatPoint {
    month: number
    month_name: string
    median_price: number
    q1_price: number
    q3_price: number
    iqr_price: number
    record_count: number
    years_of_data: number
    month_rank: number
    is_best: boolean
    is_worst: boolean
}

interface SeasonalCalendarResponse {
    commodity: string
    state: string
    total_years: number
    low_confidence: boolean
    months: MonthlyStatPoint[]
}

async function fetchSeasonalData(commodity: string, state: string): Promise<SeasonalCalendarResponse> {
    try {
        const response = await api.get("/seasonal", {
            params: { commodity, state },
        })
        return response.data
    } catch (error: any) {
        if (error.response?.status === 404) {
            throw new Error("NOT_FOUND")
        }
        throw error
    }
}

interface ChartDataPoint {
    month_name: string
    median_price: number
    errorBar: [number, number]
    is_best: boolean
    is_worst: boolean
    month_rank: number
    q1_price: number
    q3_price: number
    record_count: number
    years_of_data: number
}

// Custom tooltip for the chart
function CustomTooltip({ active, payload }: any) {
    if (!active || !payload || !payload.length) return null
    const d = payload[0].payload as ChartDataPoint
    return (
        <div className="rounded-lg border bg-background p-3 shadow-md text-sm space-y-1">
            <p className="font-semibold text-foreground">{d.month_name}</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-muted-foreground">
                <span>Median Price</span>
                <span className="text-right font-medium text-foreground">₹{d.median_price.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                <span>Q1 (25th %ile)</span>
                <span className="text-right">₹{d.q1_price.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                <span>Q3 (75th %ile)</span>
                <span className="text-right">₹{d.q3_price.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                <span>Records</span>
                <span className="text-right">{d.record_count.toLocaleString()}</span>
                <span>Years</span>
                <span className="text-right">{d.years_of_data}</span>
                <span>Rank</span>
                <span className="text-right">#{d.month_rank}</span>
            </div>
            {d.is_best && (
                <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200 mt-1">
                    <TrendingUp className="h-3 w-3 mr-1" /> Best Month
                </Badge>
            )}
            {d.is_worst && (
                <Badge className="bg-red-100 text-red-800 border-red-200 mt-1">
                    <TrendingDown className="h-3 w-3 mr-1" /> Worst Month
                </Badge>
            )}
        </div>
    )
}

export default function SeasonalCalendarPage() {
    const [commodity, setCommodity] = useState("")
    const [commoditySearch, setCommoditySearch] = useState("")
    const [isCommodityOpen, setIsCommodityOpen] = useState(false)
    const [state, setState] = useState("")
    const [searchTrigger, setSearchTrigger] = useState<{ commodity: string; state: string } | null>(null)

    // Fetch commodity and state lists from the API
    const { data: commodityList } = useQuery<string[]>({
        queryKey: ["seasonal-commodities"],
        queryFn: async () => (await api.get("/seasonal/commodities")).data,
        staleTime: 600000,
    })

    const { data: stateList } = useQuery<string[]>({
        queryKey: ["seasonal-states", commodity],
        queryFn: async () => (await api.get("/seasonal/states", { params: commodity ? { commodity } : undefined })).data,
        staleTime: 600000,
    })

    const filteredCommodities = useMemo(() => {
        if (!commodityList) return []
        if (!commoditySearch) return commodityList
        return commodityList.filter((c) => c.toLowerCase().includes(commoditySearch.toLowerCase()))
    }, [commodityList, commoditySearch])

    const { data, isLoading, error, isError } = useQuery<SeasonalCalendarResponse>({
        queryKey: ["seasonal", searchTrigger?.commodity, searchTrigger?.state],
        queryFn: () => fetchSeasonalData(searchTrigger!.commodity, searchTrigger!.state),
        enabled: !!searchTrigger,
        retry: false,
        staleTime: 300000,
    })

    const chartData: ChartDataPoint[] = useMemo(() => {
        if (!data?.months) return []
        return data.months.map((m) => ({
            month_name: m.month_name,
            median_price: m.median_price,
            // Asymmetric error bars: [median - q1, q3 - median]
            errorBar: [m.median_price - m.q1_price, m.q3_price - m.median_price] as [number, number],
            is_best: m.is_best,
            is_worst: m.is_worst,
            month_rank: m.month_rank,
            q1_price: m.q1_price,
            q3_price: m.q3_price,
            record_count: m.record_count,
            years_of_data: m.years_of_data,
        }))
    }, [data])

    const isNotFound = isError && error?.message === "NOT_FOUND"

    const handleSearch = () => {
        if (!commodity || !state) return
        setSearchTrigger({ commodity, state })
    }

    // Best and worst month summaries
    const bestMonths = data?.months?.filter((m) => m.is_best) || []
    const worstMonths = data?.months?.filter((m) => m.is_worst) || []

    return (
        <AppLayout>
            <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8">
                <div className="max-w-5xl mx-auto space-y-6">
                    {/* Header */}
                    <div className="space-y-2">
                        <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
                            <CalendarDays className="h-8 w-8 text-primary" />
                            Seasonal Price Calendar
                        </h1>
                        <p className="text-muted-foreground">
                            Discover the best months to sell your produce — based on 10 years of market data
                        </p>
                    </div>

                    {/* Search Card */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-lg">
                                <Search className="h-5 w-5 text-emerald-600" />
                                Select Commodity & State
                            </CardTitle>
                            <CardDescription>
                                Choose a commodity and state to view historical monthly price patterns
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {/* Commodity Searchable Dropdown */}
                                <div className="relative">
                                    <Label>Commodity *</Label>
                                    <div className="relative mt-1">
                                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                                        <Input
                                            placeholder="Search commodity..."
                                            value={commodity || commoditySearch}
                                            onChange={(e) => {
                                                setCommoditySearch(e.target.value)
                                                setCommodity("")
                                                setIsCommodityOpen(true)
                                            }}
                                            onFocus={() => setIsCommodityOpen(true)}
                                            className="pl-10"
                                        />
                                    </div>
                                    {isCommodityOpen && (
                                        <>
                                            <div className="fixed inset-0 z-40" onClick={() => setIsCommodityOpen(false)} />
                                            <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-md shadow-md max-h-52 overflow-y-auto">
                                                {filteredCommodities.length === 0 ? (
                                                    <div className="px-3 py-2 text-sm text-muted-foreground">
                                                        {commodityList ? "No commodities found" : "Loading..."}
                                                    </div>
                                                ) : (
                                                    filteredCommodities.map((c) => (
                                                        <div
                                                            key={c}
                                                            className={`relative flex cursor-pointer select-none items-center rounded-sm px-3 py-2 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground ${commodity === c ? "bg-accent text-accent-foreground font-medium" : ""}`}
                                                            onClick={() => {
                                                                setCommodity(c)
                                                                setCommoditySearch("")
                                                                setIsCommodityOpen(false)
                                                                setState("")
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

                                {/* State Select */}
                                <div>
                                    <Label>State *</Label>
                                    <Select value={state} onValueChange={setState}>
                                        <SelectTrigger className="mt-1"><SelectValue placeholder="Select state" /></SelectTrigger>
                                        <SelectContent>
                                            {(stateList || []).map((s) => (
                                                <SelectItem key={s} value={s}>{s}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {/* Search Button */}
                                <div>
                                    <Label>&nbsp;</Label>
                                    <Button
                                        onClick={handleSearch}
                                        disabled={isLoading || !commodity || !state}
                                        className="w-full mt-1 bg-emerald-600 hover:bg-emerald-700"
                                    >
                                        {isLoading ? (
                                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                        ) : (
                                            <CalendarDays className="h-4 w-4 mr-2" />
                                        )}
                                        View Calendar
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Loading */}
                    {isLoading && (
                        <Card>
                            <CardContent className="py-12 text-center">
                                <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground mb-3" />
                                <p className="text-muted-foreground">Loading seasonal data...</p>
                            </CardContent>
                        </Card>
                    )}

                    {/* Not Found */}
                    {isNotFound && (
                        <Card className="border-amber-300 bg-amber-50/50">
                            <CardContent className="py-8 text-center">
                                <AlertTriangle className="h-12 w-12 mx-auto text-amber-400 mb-3" />
                                <h3 className="text-lg font-semibold text-amber-700 mb-1">No Data Available</h3>
                                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                                    No seasonal data found for <strong>{searchTrigger?.commodity}</strong> in{" "}
                                    <strong>{searchTrigger?.state}</strong>. This combination may not exist in
                                    the Agmarknet dataset. Try a different commodity or state.
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {/* Error (non-404) */}
                    {isError && !isNotFound && (
                        <Card className="border-red-300 bg-red-50/50">
                            <CardContent className="py-8 text-center">
                                <AlertTriangle className="h-12 w-12 mx-auto text-red-400 mb-3" />
                                <h3 className="text-lg font-semibold text-red-700 mb-1">Something Went Wrong</h3>
                                <p className="text-sm text-muted-foreground">
                                    Failed to load seasonal data. Please try again.
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {/* Results */}
                    {data && !isLoading && (
                        <>
                            {/* Low Confidence Warning (UI-05) */}
                            {data.low_confidence && (
                                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-3">
                                    <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
                                    <div>
                                        <p className="font-medium text-amber-800">Limited Data Available</p>
                                        <p className="text-sm text-amber-700 mt-0.5">
                                            Only {data.total_years} year(s) of data available for {data.commodity} in {data.state}.
                                            Best/worst month labels require at least 3 years. Results may not reflect typical patterns.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Summary Cards */}
                            {!data.low_confidence && (bestMonths.length > 0 || worstMonths.length > 0) && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {bestMonths.length > 0 && (
                                        <Card className="border-emerald-200 bg-emerald-50/30">
                                            <CardContent className="py-4">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <TrendingUp className="h-5 w-5 text-emerald-600" />
                                                    <span className="font-semibold text-emerald-800">Best Months to Sell</span>
                                                </div>
                                                <div className="flex gap-2 flex-wrap">
                                                    {bestMonths.map((m) => (
                                                        <Badge key={m.month} className="bg-emerald-100 text-emerald-800 border-emerald-200 text-sm px-3 py-1">
                                                            {m.month_name} — ₹{m.median_price.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </CardContent>
                                        </Card>
                                    )}
                                    {worstMonths.length > 0 && (
                                        <Card className="border-red-200 bg-red-50/30">
                                            <CardContent className="py-4">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <TrendingDown className="h-5 w-5 text-red-600" />
                                                    <span className="font-semibold text-red-800">Lowest Price Month</span>
                                                </div>
                                                <div className="flex gap-2 flex-wrap">
                                                    {worstMonths.map((m) => (
                                                        <Badge key={m.month} className="bg-red-100 text-red-800 border-red-200 text-sm px-3 py-1">
                                                            {m.month_name} — ₹{m.median_price.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </CardContent>
                                        </Card>
                                    )}
                                </div>
                            )}

                            {/* Chart */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center justify-between">
                                        <span>Monthly Price Pattern</span>
                                        <Badge variant="outline" className="font-normal">
                                            {data.commodity} — {data.state} · {data.total_years} year{data.total_years > 1 ? "s" : ""} of data
                                        </Badge>
                                    </CardTitle>
                                    <CardDescription>
                                        Bars show median price per month. Error bars show interquartile range (Q1–Q3).
                                        Green = best month(s) to sell, Red = worst month.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="w-full h-[400px]">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <ComposedChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                                                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                                                <XAxis
                                                    dataKey="month_name"
                                                    tick={{ fontSize: 12 }}
                                                    axisLine={{ stroke: 'hsl(var(--border))' }}
                                                />
                                                <YAxis
                                                    tick={{ fontSize: 12 }}
                                                    tickFormatter={(v: number) => `₹${v.toLocaleString()}`}
                                                    axisLine={{ stroke: 'hsl(var(--border))' }}
                                                    label={{
                                                        value: "Price (₹/quintal)",
                                                        angle: -90,
                                                        position: "insideLeft",
                                                        style: { fontSize: 12, fill: 'hsl(var(--muted-foreground))' },
                                                    }}
                                                />
                                                <Tooltip content={<CustomTooltip />} />
                                                <Legend
                                                    content={() => (
                                                        <div className="flex justify-center gap-4 mt-2 text-xs">
                                                            <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm" style={{ background: '#10b981' }} /> Best Month</span>
                                                            <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm" style={{ background: '#ef4444' }} /> Worst Month</span>
                                                            <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm" style={{ background: '#6b7280' }} /> Normal</span>
                                                        </div>
                                                    )}
                                                />
                                                <Bar dataKey="median_price" name="Median Price" radius={[4, 4, 0, 0]}>
                                                    {chartData.map((entry, index) => (
                                                        <Cell
                                                            key={`cell-${index}`}
                                                            fill={
                                                                entry.is_best ? '#10b981' :
                                                                    entry.is_worst ? '#ef4444' :
                                                                        '#6b7280'
                                                            }
                                                            fillOpacity={0.8}
                                                        />
                                                    ))}
                                                    <ErrorBar
                                                        dataKey="errorBar"
                                                        stroke="#374151"
                                                        strokeWidth={1.5}
                                                        width={6}
                                                    />
                                                </Bar>
                                            </ComposedChart>
                                        </ResponsiveContainer>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Data Info Footer */}
                            <div className="flex items-center gap-2 text-xs text-muted-foreground px-1">
                                <Info className="h-3.5 w-3.5" />
                                <span>
                                    Prices are median modal prices from Agmarknet data ({data.total_years} years).
                                    Error bars represent interquartile range (25th–75th percentile).
                                </span>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </AppLayout>
    )
}
