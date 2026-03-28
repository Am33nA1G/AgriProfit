"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { TrendingUp, AlertTriangle, MapPin, Clock, Truck, ChevronDown, Search } from "lucide-react"
import { toast } from "sonner"
import { AppLayout } from "@/components/layout/AppLayout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { arbitrageService, ArbitrageResult, ArbitrageResponse } from "@/services/arbitrage"

type VerdictColour = "default" | "secondary" | "destructive" | "outline"

function getVerdictBadgeVariant(verdict: string): VerdictColour {
    switch (verdict) {
        case "excellent":
            return "default"
        case "good":
            return "secondary"
        case "marginal":
            return "outline"
        case "not_viable":
            return "destructive"
        default:
            return "outline"
    }
}

function getVerdictBadgeClass(verdict: string): string {
    switch (verdict) {
        case "excellent":
            return "bg-green-500 text-white hover:bg-green-600"
        case "good":
            return "bg-blue-500 text-white hover:bg-blue-600"
        case "marginal":
            return "bg-yellow-500 text-white hover:bg-yellow-600"
        case "not_viable":
            return "bg-red-500 text-white hover:bg-red-600"
        default:
            return ""
    }
}

function VerdictBadge({ verdict }: { verdict: string }) {
    return (
        <Badge
            variant={getVerdictBadgeVariant(verdict)}
            className={getVerdictBadgeClass(verdict)}
        >
            {verdict.replace("_", " ")}
        </Badge>
    )
}

/* ─── Searchable Dropdown ─── */
function SearchableDropdown({
    id,
    label,
    placeholder,
    options,
    value,
    onChange,
    isLoading,
}: {
    id: string
    label: string
    placeholder: string
    options: string[]
    value: string
    onChange: (v: string) => void
    isLoading: boolean
}) {
    const [open, setOpen] = useState(false)
    const [search, setSearch] = useState("")
    const ref = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
        }
        document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [])

    const filtered = useMemo(
        () =>
            options.filter((o) =>
                o.toLowerCase().includes(search.toLowerCase())
            ),
        [options, search]
    )

    return (
        <div className="space-y-2" ref={ref}>
            <Label htmlFor={id}>{label}</Label>
            <div className="relative">
                <button
                    id={id}
                    type="button"
                    onClick={() => setOpen(!open)}
                    className="flex items-center justify-between w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                    <span className={value ? "text-foreground" : "text-muted-foreground"}>
                        {value || placeholder}
                    </span>
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                </button>

                {open && (
                    <div className="absolute z-50 mt-1 w-full rounded-md border border-border bg-card shadow-lg">
                        {/* search box */}
                        <div className="flex items-center border-b border-border px-3 py-2">
                            <Search className="h-4 w-4 text-muted-foreground mr-2 flex-shrink-0" />
                            <input
                                autoFocus
                                type="text"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Type to search..."
                                className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                            />
                        </div>
                        {/* options list */}
                        <ul className="max-h-56 overflow-y-auto py-1">
                            {isLoading && (
                                <li className="px-3 py-2 text-sm text-muted-foreground">Loading...</li>
                            )}
                            {!isLoading && filtered.length === 0 && (
                                <li className="px-3 py-2 text-sm text-muted-foreground">No matches</li>
                            )}
                            {filtered.map((opt) => (
                                <li
                                    key={opt}
                                    onClick={() => {
                                        onChange(opt)
                                        setOpen(false)
                                        setSearch("")
                                    }}
                                    className={`cursor-pointer px-3 py-2 text-sm transition-colors hover:bg-muted ${opt === value
                                        ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 font-medium"
                                        : "text-foreground"
                                        }`}
                                >
                                    {opt}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    )
}

/* ─── Results Table ─── */
function ResultsTable({ data }: { data: ArbitrageResponse }) {
    const { results, suppressed_count, threshold_pct, distance_note } = data

    if (results.length === 0) {
        if (suppressed_count > 0) {
            return (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-6 text-center">
                    <p className="text-sm text-yellow-800">
                        All {suppressed_count} results were below the {threshold_pct}% net margin threshold — no profitable arbitrage found.
                    </p>
                </div>
            )
        }
        return (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center">
                <p className="text-sm text-muted-foreground">
                    No arbitrage opportunities found for this commodity and district.
                </p>
            </div>
        )
    }

    return (
        <div className="space-y-3">
            <div className="overflow-x-auto rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Mandi</TableHead>
                            <TableHead>District</TableHead>
                            <TableHead className="text-right">Distance (km)</TableHead>
                            <TableHead className="text-right">Time (h)</TableHead>
                            <TableHead className="text-right">Freight (Rs/q)</TableHead>
                            <TableHead className="text-right">Spoilage (%)</TableHead>
                            <TableHead className="text-right">Net Profit (Rs/q)</TableHead>
                            <TableHead>Verdict</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {results.map((result: ArbitrageResult) => (
                            <TableRow
                                key={`${result.mandi_name}-${result.district}`}
                                className={result.is_stale ? "opacity-60" : undefined}
                            >
                                <TableCell>
                                    <div>
                                        <span className="font-medium">{result.mandi_name}</span>
                                        {result.days_since_update > 0 && (
                                            <p className="text-xs text-muted-foreground mt-0.5">
                                                ({result.days_since_update} days ago)
                                            </p>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell>{result.district}</TableCell>
                                <TableCell className="text-right">{result.distance_km.toFixed(1)}</TableCell>
                                <TableCell className="text-right">{result.travel_time_hours.toFixed(1)}</TableCell>
                                <TableCell className="text-right">
                                    {result.freight_cost_per_quintal.toFixed(0)}
                                </TableCell>
                                <TableCell className="text-right">{result.spoilage_percent.toFixed(1)}</TableCell>
                                <TableCell
                                    className={`text-right font-semibold ${result.net_profit_per_quintal > 0
                                        ? "text-green-600"
                                        : "text-red-600"
                                        }`}
                                >
                                    {result.net_profit_per_quintal.toFixed(0)}
                                </TableCell>
                                <TableCell>
                                    <VerdictBadge verdict={result.verdict} />
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
            {suppressed_count > 0 && (
                <p className="text-xs text-muted-foreground">
                    {suppressed_count} additional mandi(s) were below the {threshold_pct}% margin threshold and not shown.
                </p>
            )}
            {distance_note && (
                <p className="text-xs text-muted-foreground">{distance_note}</p>
            )}
        </div>
    )
}

/* ─── Page ─── */
export default function ArbitragePage() {
    const [commodity, setCommodity] = useState("")
    const [state, setState] = useState("")
    const [district, setDistrict] = useState("")
    const [submitted, setSubmitted] = useState(false)

    /* Fetch dropdown options */
    const { data: commodityOptions = [], isLoading: loadingCommodities } = useQuery<string[]>({
        queryKey: ["arbitrage-commodities"],
        queryFn: () => arbitrageService.getCommodities(),
        staleTime: 10 * 60 * 1000,
    })

    const { data: stateOptions = [], isLoading: loadingStates } = useQuery<string[]>({
        queryKey: ["arbitrage-states"],
        queryFn: () => arbitrageService.getStates(),
        staleTime: 10 * 60 * 1000,
    })

    const { data: districtOptions = [], isLoading: loadingDistricts } = useQuery<string[]>({
        queryKey: ["arbitrage-districts", state],
        queryFn: () => arbitrageService.getDistricts(state),
        enabled: !!state,
        staleTime: 10 * 60 * 1000,
    })

    /* Fetch arbitrage results */
    const { data, isLoading, error } = useQuery<ArbitrageResponse>({
        queryKey: ["arbitrage", commodity, district],
        queryFn: () => arbitrageService.getResults(commodity, district),
        enabled: submitted && !!commodity && !!district,
        staleTime: 5 * 60 * 1000,
    })

    if (error) {
        toast.error("Failed to fetch arbitrage data. Please try again.")
    }

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        if (!commodity.trim() || !state.trim() || !district.trim()) {
            toast.error("Please select commodity, state, and district.")
            return
        }
        setSubmitted(true)
    }

    function handleCommodityChange(value: string) {
        setCommodity(value)
        setSubmitted(false)
    }

    function handleStateChange(value: string) {
        setState(value)
        setDistrict("")
        setSubmitted(false)
    }

    function handleDistrictChange(value: string) {
        setDistrict(value)
        setSubmitted(false)
    }

    return (
        <AppLayout>
            <div className="p-6 space-y-6">
                <div className="flex items-center gap-3">
                    <TrendingUp className="h-7 w-7 text-primary" />
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">Mandi Arbitrage Dashboard</h1>
                        <p className="text-sm text-muted-foreground mt-0.5">
                            Find the most profitable mandis to sell your commodity from your district
                        </p>
                    </div>
                </div>

                {/* Search Form */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Find Opportunities</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                                <SearchableDropdown
                                    id="commodity"
                                    label="Commodity"
                                    placeholder="Select a commodity"
                                    options={commodityOptions}
                                    value={commodity}
                                    onChange={handleCommodityChange}
                                    isLoading={loadingCommodities}
                                />
                                <SearchableDropdown
                                    id="state"
                                    label="Origin State"
                                    placeholder="Select a state"
                                    options={stateOptions}
                                    value={state}
                                    onChange={handleStateChange}
                                    isLoading={loadingStates}
                                />
                                <SearchableDropdown
                                    id="district"
                                    label="Origin District"
                                    placeholder={state ? "Select a district" : "Select a state first"}
                                    options={districtOptions}
                                    value={district}
                                    onChange={handleDistrictChange}
                                    isLoading={loadingDistricts}
                                />
                            </div>
                            <Button type="submit" disabled={isLoading}>
                                {isLoading ? "Searching..." : "Find Opportunities"}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {/* Stale data warning */}
                {data?.has_stale_data && (
                    <Alert className="border-yellow-300 bg-yellow-50">
                        <AlertTriangle className="h-4 w-4 text-yellow-600" />
                        <AlertDescription className="text-yellow-800">
                            Data last updated {data.data_reference_date} — signal may be outdated
                        </AlertDescription>
                    </Alert>
                )}

                {/* Loading state */}
                {isLoading && (
                    <div className="text-muted-foreground text-sm py-4">
                        Searching for arbitrage opportunities...
                    </div>
                )}

                {/* Error state */}
                {error && !isLoading && (
                    <Alert variant="destructive">
                        <AlertDescription>
                            Failed to load arbitrage data. Please check your inputs and try again.
                        </AlertDescription>
                    </Alert>
                )}

                {/* Results */}
                {data && !isLoading && (
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <MapPin className="h-4 w-4" />
                            <span>
                                Showing top results for <strong>{data.commodity}</strong> from{" "}
                                <strong>{data.origin_district}</strong>
                            </span>
                            {data.results.length > 0 && (
                                <>
                                    <Truck className="h-4 w-4 ml-2" />
                                    <span>{data.results.length} mandi(s) found</span>
                                    <Clock className="h-4 w-4 ml-2" />
                                    <span>Reference date: {data.data_reference_date}</span>
                                </>
                            )}
                        </div>
                        <ResultsTable data={data} />
                    </div>
                )}
            </div>
        </AppLayout>
    )
}

