"use client"

import {
    ComposedChart,
    Area,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from "recharts"
import type { ForecastPoint } from "@/services/forecast"

interface ForecastChartProps {
    forecastPoints: ForecastPoint[]
    confidenceColour: "Green" | "Yellow" | "Red"
    commodity: string
}

const COLOUR_MAP: Record<string, { line: string; band: string; bandFill: string }> = {
    Green: {
        line: "#10b981",
        band: "#6ee7b7",
        bandFill: "rgba(16, 185, 129, 0.12)",
    },
    Yellow: {
        line: "#f59e0b",
        band: "#fbbf24",
        bandFill: "rgba(245, 158, 11, 0.12)",
    },
    Red: {
        line: "#ef4444",
        band: "#f87171",
        bandFill: "rgba(239, 68, 68, 0.12)",
    },
}

export default function ForecastChart({
    forecastPoints,
    confidenceColour,
    commodity,
}: ForecastChartProps) {
    const colours = COLOUR_MAP[confidenceColour] || COLOUR_MAP.Yellow

    if (!forecastPoints || forecastPoints.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 bg-muted/30 rounded-xl border border-border/50">
                <p className="text-muted-foreground text-sm">No forecast data available</p>
            </div>
        )
    }

    // Compute Y-axis bounds from actual prices (not stacked-from-0)
    const allPrices = forecastPoints.flatMap((p) =>
        [p.price_low, p.price_mid, p.price_high].filter((v): v is number => v != null)
    )
    const minPrice = Math.min(...allPrices)
    const maxPrice = Math.max(...allPrices)
    const pad = Math.max((maxPrice - minPrice) * 0.2, maxPrice * 0.04)
    const yMin = Math.floor(minPrice - pad)
    const yMax = Math.ceil(maxPrice + pad)

    // Format data for Recharts
    const chartData = forecastPoints.map((p) => ({
        date: p.date,
        mid: p.price_mid,
        low: p.price_low,
        high: p.price_high,
        // For the Area band: low is the base, bandRange is high - low
        bandRange: p.price_high && p.price_low ? p.price_high - p.price_low : 0,
    }))

    return (
        <div className="w-full h-80" id="forecast-chart">
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                    data={chartData}
                    margin={{ top: 10, right: 20, bottom: 20, left: 10 }}
                >
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                    <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                        tickFormatter={(val) => {
                            const d = new Date(val)
                            return `${d.getDate()}/${d.getMonth() + 1}`
                        }}
                    />
                    <YAxis
                        tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                        domain={[yMin, yMax]}
                        tickFormatter={(val) => `₹${Math.round(val).toLocaleString("en-IN")}`}
                        width={70}
                    />
                    <Tooltip
                        contentStyle={{
                            background: "hsl(var(--popover))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: "8px",
                            fontSize: 12,
                            color: "hsl(var(--foreground))",
                        }}
                        formatter={(value?: number, name?: string) => {
                            const labels: Record<string, string> = {
                                mid: "Predicted",
                                low: "Low",
                                high: "High",
                            }
                            return [`₹${value?.toFixed(2) ?? "N/A"}`, labels[name ?? ""] || name || ""]
                        }}
                        labelFormatter={(label) => {
                            const d = new Date(label)
                            return d.toLocaleDateString("en-IN", {
                                day: "numeric",
                                month: "short",
                                year: "numeric",
                            })
                        }}
                    />
                    <Legend verticalAlign="top" height={30} />

                    {/* Confidence band — low to high */}
                    <Area
                        dataKey="low"
                        stackId="band"
                        stroke="none"
                        fill="transparent"
                        name="Low"
                        dot={false}
                    />
                    <Area
                        dataKey="bandRange"
                        stackId="band"
                        stroke="none"
                        fill={colours.bandFill}
                        name="Confidence Band"
                        dot={false}
                    />

                    {/* Forecast mid-line */}
                    <Line
                        dataKey="mid"
                        stroke={colours.line}
                        strokeWidth={2.5}
                        name="Predicted"
                        dot={false}
                        activeDot={{ r: 4, stroke: colours.line, strokeWidth: 2 }}
                    />
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    )
}
