"use client"

import React, { useState, useEffect } from "react"
import dynamic from "next/dynamic"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { LineChart, Table as TableIcon, Download, Info } from "lucide-react"
import { forecastsService, ForecastResponse } from "@/services/forecasts"
import { ForecastTable } from "./forecast/ForecastTable"
import { RecommendationsPanel } from "./forecast/RecommendationsPanel"

// Lazy load chart component (recharts-dependent)
const ForecastChart = dynamic(
    () => import("./forecast/ForecastChart").then(m => m.ForecastChart),
    { ssr: false, loading: () => <div className="h-[400px] flex items-center justify-center text-muted-foreground">Loading chart...</div> }
)
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

export function PriceForecastSection() {
    const [data, setData] = useState<ForecastResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [commodity, setCommodity] = useState("Wheat")
    const [days, setDays] = useState("30")
    const [view, setView] = useState("chart") // chart | table

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true)
            try {
                const result = await forecastsService.getForecasts(commodity, parseInt(days))
                setData(result)
            } catch (error) {
                console.error(error)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [commodity, days])

    const handleExport = () => {
        if (!data || !data.forecasts) return
        const headers = "Date,Predicted Price,Confidence,Recommendation\n"
        const csv = headers + data.forecasts.map(row => `${row.date},${row.predicted_price},${row.confidence},${row.recommendation}`).join("\n")
        const blob = new Blob([csv], { type: "text/csv" })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `forecast_${commodity}_${days}d.csv`
        a.click()
    }

    return (
        <Card className="w-full">
            <CardHeader className="pb-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <CardTitle className="text-xl flex items-center gap-2">
                            Start AI Forecast Engine
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger>
                                        <Info className="h-4 w-4 text-muted-foreground" />
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        <p>Powered by proprietary ML models analyzing<br />historical prices, weather, and market trends.</p>
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        </CardTitle>
                        <CardDescription>
                            Predictive analysis for better decision making
                        </CardDescription>
                    </div>

                    <div className="flex items-center gap-2">
                        <Select value={commodity} onValueChange={setCommodity}>
                            <SelectTrigger className="w-[140px]">
                                <SelectValue placeholder="Commodity" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="Wheat">Wheat</SelectItem>
                                <SelectItem value="Rice">Rice</SelectItem>
                                <SelectItem value="Potato">Potato</SelectItem>
                                <SelectItem value="Onion">Onion</SelectItem>
                            </SelectContent>
                        </Select>

                        <Select value={days} onValueChange={setDays}>
                            <SelectTrigger className="w-[120px]">
                                <SelectValue placeholder="Period" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="7">7 Days</SelectItem>
                                <SelectItem value="30">30 Days</SelectItem>
                                <SelectItem value="90">90 Days</SelectItem>
                            </SelectContent>
                        </Select>

                        <div className="border-l pl-2 ml-2 flex gap-1">
                            <Button
                                variant={view === "chart" ? "secondary" : "ghost"}
                                size="icon"
                                onClick={() => setView("chart")}
                                title="Chart View"
                            >
                                <LineChart className="h-4 w-4" />
                            </Button>
                            <Button
                                variant={view === "table" ? "secondary" : "ghost"}
                                size="icon"
                                onClick={() => setView("table")}
                                title="Table View"
                            >
                                <TableIcon className="h-4 w-4" />
                            </Button>
                        </div>

                        <Button variant="outline" size="icon" onClick={handleExport} title="Export CSV">
                            <Download className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="space-y-6">
                {loading ? (
                    <div className="h-[400px] flex items-center justify-center">
                        <div className="flex flex-col items-center gap-2">
                            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                            <p className="text-sm text-muted-foreground">Generating forecast...</p>
                        </div>
                    </div>
                ) : data && Array.isArray(data.forecasts) ? (
                    <>
                        <div className="min-h-[400px]">
                            {view === "chart" ? (
                                <ForecastChart data={data.forecasts} currentPrice={data.current_price} />
                            ) : (
                                <ForecastTable data={data.forecasts} currentPrice={data.current_price} />
                            )}
                        </div>

                        <div className="border-t pt-6">
                            <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">AI Recommendations</h3>
                            <RecommendationsPanel summary={data.summary} />
                        </div>

                        <p className="text-xs text-center text-muted-foreground mt-4 italic">
                            Disclaimer: Forecasts are predictions based on available data and are not guaranteed. Please use your own judgment.
                        </p>
                    </>
                ) : (
                    <div className="h-[400px] flex items-center justify-center text-muted-foreground">
                        Failed to load forecast data.
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
