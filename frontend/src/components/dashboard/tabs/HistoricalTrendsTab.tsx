"use client"

import React, { useState, useEffect } from "react"
import dynamic from "next/dynamic"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Download, Loader2 } from "lucide-react"
import { pricesService, HistoricalPrice } from "@/services/prices"
import { commoditiesService } from "@/services/commodities"

// Dynamic import recharts for code splitting
const LineChart = dynamic(() => import("recharts").then(m => m.LineChart), { ssr: false })
const Line = dynamic(() => import("recharts").then(m => m.Line), { ssr: false })
const XAxis = dynamic(() => import("recharts").then(m => m.XAxis), { ssr: false })
const YAxis = dynamic(() => import("recharts").then(m => m.YAxis), { ssr: false })
const CartesianGrid = dynamic(() => import("recharts").then(m => m.CartesianGrid), { ssr: false })
const Tooltip = dynamic(() => import("recharts").then(m => m.Tooltip), { ssr: false })
const ResponsiveContainer = dynamic(() => import("recharts").then(m => m.ResponsiveContainer), { ssr: false })

export function HistoricalTrendsTab() {
    const [data, setData] = useState<HistoricalPrice[]>([])
    const [commodities, setCommodities] = useState<string[]>([])
    const [loading, setLoading] = useState(true)
    const [commoditiesLoading, setCommoditiesLoading] = useState(true)
    const [commodity, setCommodity] = useState("Wheat")
    const [duration, setDuration] = useState("30")

    // Load all commodities for dropdown
    useEffect(() => {
        const fetchCommodities = async () => {
            try {
                const allCommodities = await commoditiesService.getAll({ limit: 500 })
                const names = allCommodities.map(c => c.name).sort()
                setCommodities(names)
                if (names.length > 0 && !names.includes("Wheat")) {
                    setCommodity(names[0])
                }
            } catch (error) {
                console.error("Failed to load commodities", error)
                // Fallback to hardcoded list
                setCommodities(["Wheat", "Rice", "Potato", "Onion", "Tomato"])
            } finally {
                setCommoditiesLoading(false)
            }
        }
        fetchCommodities()
    }, [])

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true)
            try {
                const result = await pricesService.getHistoricalPrices({
                    commodity,
                    mandi_id: "all",
                    days: parseInt(duration)
                })
                setData(result.data)
            } catch (error) {
                console.error(error)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [commodity, duration])

    const handleExport = () => {
        const headers = "Date,Price\n"
        const csv = headers + data.map(row => `${row.date},${row.price}`).join("\n")
        const blob = new Blob([csv], { type: "text/csv" })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `price_history_${commodity}_${duration}d.csv`
        a.click()
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between gap-4">
                <div className="flex items-center gap-3">
                    <Select value={commodity} onValueChange={setCommodity} disabled={commoditiesLoading}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Select Commodity" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[300px]">
                            {commoditiesLoading ? (
                                <SelectItem value="loading" disabled>Loading...</SelectItem>
                            ) : commodities.length > 0 ? (
                                commodities.map((name) => (
                                    <SelectItem key={name} value={name}>
                                        {name}
                                    </SelectItem>
                                ))
                            ) : (
                                <SelectItem value="none" disabled>No commodities</SelectItem>
                            )}
                        </SelectContent>
                    </Select>

                    <Select value={duration} onValueChange={setDuration}>
                        <SelectTrigger className="w-[140px]">
                            <SelectValue placeholder="Duration" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="7">Last 7 Days</SelectItem>
                            <SelectItem value="30">Last 30 Days</SelectItem>
                            <SelectItem value="90">Last 90 Days</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <Button variant="outline" size="sm" onClick={handleExport} disabled={data.length === 0}>
                    <Download className="h-4 w-4 mr-2" />
                    Export CSV
                </Button>
            </div>

            <div className="h-[300px] w-full border rounded-lg p-4 bg-card">
                {loading ? (
                    <div className="h-full w-full flex items-center justify-center">
                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                ) : data.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground)/0.2)" />
                            <XAxis
                                dataKey="date"
                                tickFormatter={(val) => {
                                    const date = new Date(val)
                                    return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
                                }}
                                stroke="hsl(var(--muted-foreground))"
                                fontSize={12}
                                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                            />
                            <YAxis
                                domain={['dataMin - 100', 'dataMax + 100']}
                                stroke="hsl(var(--muted-foreground))"
                                fontSize={12}
                                tickFormatter={(val) => `₹${Math.round(val)}`}
                                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                                label={{ 
                                    value: '₹ per Quintal', 
                                    angle: -90, 
                                    position: 'insideLeft', 
                                    style: { textAnchor: 'middle', fontSize: 11, fill: 'hsl(var(--muted-foreground))' } 
                                }}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: 'hsl(var(--popover))',
                                    border: '1px solid hsl(var(--border))',
                                    borderRadius: 'var(--radius)',
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                                    color: 'hsl(var(--popover-foreground))'
                                }}
                                labelFormatter={(val) => new Date(val).toLocaleDateString('en-IN', { 
                                    weekday: 'short',
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                })}
                                formatter={(value: any) => [`₹${Number(value).toFixed(2)} per quintal`, "Price"]}
                            />
                            <Line
                                type="monotone"
                                dataKey="price"
                                stroke="#2563eb"
                                strokeWidth={3}
                                dot={{ 
                                    r: 4, 
                                    fill: '#2563eb',
                                    strokeWidth: 2,
                                    stroke: '#ffffff'
                                }}
                                activeDot={{ r: 6, fill: '#2563eb' }}
                                isAnimationActive={true}
                                animationDuration={800}
                                connectNulls={true}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="h-full w-full flex items-center justify-center text-muted-foreground">
                        No data available
                    </div>
                )}
            </div>
        </div>
    )
}
