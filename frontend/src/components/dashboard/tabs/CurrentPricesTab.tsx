"use client"

import React, { useState, useEffect } from "react"
import Link from "next/link"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, ArrowUpRight, ArrowDownRight, Search } from "lucide-react"
import { pricesService, MarketPrice } from "@/services/prices"
import { mandisService } from "@/services/mandis"
import { toast } from "sonner"

export function CurrentPricesTab() {
    const [prices, setPrices] = useState<MarketPrice[]>([])
    const [states, setStates] = useState<string[]>([])
    const [loading, setLoading] = useState(true)
    const [statesLoading, setStatesLoading] = useState(true)
    const [search, setSearch] = useState("")
    const [stateFilter, setStateFilter] = useState("all")
    const [displayCount, setDisplayCount] = useState(10)

    // Load states on mount
    useEffect(() => {
        const fetchStates = async () => {
            try {
                const statesList = await mandisService.getStates()
                setStates(statesList.sort())
            } catch (error) {
                console.error("Failed to load states", error)
                // Fallback to hardcoded list
                setStates(["Kerala", "Tamil Nadu", "Karnataka", "Delhi", "Maharashtra"])
            } finally {
                setStatesLoading(false)
            }
        }
        fetchStates()
    }, [])

    const fetchData = async () => {
        setLoading(true)
        try {
            const { prices } = await pricesService.getCurrentPrices({
                commodity: search || undefined,
                state: stateFilter !== "all" ? stateFilter : undefined
            })
            setPrices(prices)
        } catch (error) {
            toast.error("Failed to load prices")
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        // Debounce search
        const timer = setTimeout(() => {
            fetchData()
            setDisplayCount(10) // Reset display count when filters change
        }, 500)
        return () => clearTimeout(timer)
    }, [search, stateFilter])

    return (
        <div className="space-y-4">
            {/* Info Banner */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                <div className="flex items-start gap-2">
                    <div className="text-blue-600 dark:text-blue-400 mt-0.5">
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium text-blue-900 dark:text-blue-100">Enhanced Price Information</p>
                        <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                            <strong>7-Day Avg:</strong> Compare current price with weekly average • <strong>30-Day Range:</strong> See price volatility • <strong>Trend:</strong> Rising/Falling/Stable indicator based on recent pattern
                        </p>
                    </div>
                </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search commodity..."
                        className="pl-8"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <Select value={stateFilter} onValueChange={setStateFilter} disabled={statesLoading}>
                    <SelectTrigger className="w-full sm:w-[180px]">
                        <SelectValue placeholder="Filter by State" />
                    </SelectTrigger>
                    <SelectContent className="max-h-[300px]">
                        <SelectItem value="all">All States</SelectItem>
                        {statesLoading ? (
                            <SelectItem value="loading" disabled>Loading...</SelectItem>
                        ) : states.length > 0 ? (
                            states.map((state) => (
                                <SelectItem key={state} value={state}>
                                    {state}
                                </SelectItem>
                            ))
                        ) : (
                            <SelectItem value="none" disabled>No states found</SelectItem>
                        )}
                    </SelectContent>
                </Select>
            </div>

            <div className="rounded-md border overflow-hidden">
                <div className="overflow-x-auto">
                    <Table className="min-w-[900px]">
                        <TableHeader>
                            <TableRow>
                                <TableHead>Commodity</TableHead>
                                <TableHead>Mandi</TableHead>
                                <TableHead className="text-right">Price (₹/kg)</TableHead>
                                <TableHead className="text-right">7-Day Avg</TableHead>
                                <TableHead className="text-right">30-Day Range</TableHead>
                                <TableHead className="text-center">Trend</TableHead>
                                <TableHead className="text-right">Change</TableHead>
                                <TableHead className="text-right">Last Updated</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={8} className="h-24 text-center">
                                        <div className="flex justify-center items-center">
                                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : prices.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                                        No prices found
                                    </TableCell>
                                </TableRow>
                            ) : (
                                prices.slice(0, displayCount).map((price, index) => {
                                    const isPriceAboveAvg = price.avg_7d && price.price_per_quintal > price.avg_7d;
                                    const isPriceBelowAvg = price.avg_7d && price.price_per_quintal < price.avg_7d;
                                    
                                    return (
                                        <TableRow key={index}>
                                            <TableCell className="font-medium">
                                                <Link 
                                                    href={`/commodities/${price.commodity_id}`}
                                                    className="hover:text-primary hover:underline transition-colors"
                                                >
                                                    {price.commodity}
                                                </Link>
                                                <div className="text-xs text-muted-foreground sm:hidden">
                                                    {price.state}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                {price.mandi_name}
                                                <div className="text-xs text-muted-foreground hidden sm:block">
                                                    {price.district}, {price.state}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="font-semibold">₹{price.price_per_quintal.toFixed(2)}</div>
                                                <div className="text-xs text-muted-foreground">
                                                    ₹{price.min_price.toFixed(0)} - ₹{price.max_price.toFixed(0)}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                {price.avg_7d ? (
                                                    <>
                                                        <div className="font-medium">₹{price.avg_7d.toFixed(2)}</div>
                                                        <div className={`text-xs ${isPriceAboveAvg ? 'text-green-600' : isPriceBelowAvg ? 'text-red-600' : 'text-muted-foreground'}`}>
                                                            {isPriceAboveAvg ? 'Above avg' : isPriceBelowAvg ? 'Below avg' : 'At avg'}
                                                        </div>
                                                    </>
                                                ) : (
                                                    <span className="text-muted-foreground text-sm">N/A</span>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-right">
                                                {price.min_30d && price.max_30d ? (
                                                    <>
                                                        <div className="font-medium text-sm">
                                                            ₹{price.min_30d.toFixed(0)} - ₹{price.max_30d.toFixed(0)}
                                                        </div>
                                                        <div className="text-xs text-muted-foreground">
                                                            Range: ₹{(price.max_30d - price.min_30d).toFixed(0)}
                                                        </div>
                                                    </>
                                                ) : (
                                                    <span className="text-muted-foreground text-sm">N/A</span>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                                                    price.trend === 'up' 
                                                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                                        : price.trend === 'down'
                                                        ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                                        : 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400'
                                                }`}>
                                                    {price.trend === 'up' && <ArrowUpRight className="h-3 w-3" />}
                                                    {price.trend === 'down' && <ArrowDownRight className="h-3 w-3" />}
                                                    {price.trend === 'up' ? 'Rising' : price.trend === 'down' ? 'Falling' : 'Stable'}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className={`flex items-center justify-end gap-1 ${price.change_percent >= 0 ? "text-green-600" : "text-red-600"
                                                    }`}>
                                                    {price.change_percent >= 0 ? (
                                                        <ArrowUpRight className="h-4 w-4" />
                                                    ) : (
                                                        <ArrowDownRight className="h-4 w-4" />
                                                    )}
                                                    <span className="font-medium">{Math.abs(price.change_percent)}%</span>
                                                </div>
                                                <div className="text-xs text-muted-foreground">
                                                    {price.change_amount > 0 ? "+" : ""}
                                                    ₹{price.change_amount.toFixed(2)}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right text-muted-foreground text-sm">
                                                {new Date(price.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </TableCell>
                                        </TableRow>
                                    );
                                })
                            )}
                        </TableBody>
                    </Table>
                </div>
            </div>

            {!loading && prices.length > displayCount && (
                <div className="flex justify-center pt-4">
                    <Button
                        onClick={() => setDisplayCount(prev => prev + 10)}
                        variant="outline"
                        className="gap-2"
                    >
                        Load More ({prices.length - displayCount} remaining)
                    </Button>
                </div>
            )}
        </div>
    )
}
