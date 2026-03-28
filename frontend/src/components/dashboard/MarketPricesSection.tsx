"use client"

import React, { useState, useEffect } from "react"
import dynamic from "next/dynamic"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { RefreshCw, TrendingUp } from "lucide-react"

import { CurrentPricesTab } from "./tabs/CurrentPricesTab"

// Lazy load heavy tab components (recharts-dependent)
const HistoricalTrendsTab = dynamic(
    () => import("./tabs/HistoricalTrendsTab").then(m => m.HistoricalTrendsTab),
    { ssr: false, loading: () => <div className="h-[300px] flex items-center justify-center text-muted-foreground">Loading chart...</div> }
)
const TopMoversTab = dynamic(
    () => import("./tabs/TopMoversTab").then(m => m.TopMoversTab),
    { ssr: false }
)

export function MarketPricesSection() {
    const [lastUpdated, setLastUpdated] = useState<Date>(new Date())
    const [refreshing, setRefreshing] = useState(false)

    // Use a key to force re-render children on manual refresh
    // For polling, children usually handle their own state, but we can signal refresh too
    // A cleaner way is letting children fetch on mount, and we just provide a refresh signal if needed.
    // For simplicity, we just remount tabs on manual refresh or let them handle own data.
    // The requirement says "poll every 60 seconds".
    // Let's rely on the children's internal effects for simplicity, or just update query key if using React Query (but we are native state).
    // We'll pass a `refreshTrigger` prop if we wanted strict control, but for now we'll just show the update time.
    // Actually, to support the requirement "Updates automatically", we can just pass a timestamp prop to children
    // and they add it to dependency array of useEffect.

    const [refreshKey, setRefreshKey] = useState(0)

    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
        // Data sync happens every 6 hours (at 00:00, 06:00, 12:00, 18:00)
        // Refresh page data every 6 hours to match backend sync schedule
        const SIX_HOURS_MS = 6 * 60 * 60 * 1000
        const interval = setInterval(() => {
            handleRefresh()
        }, SIX_HOURS_MS)
        return () => clearInterval(interval)
    }, [])

    const handleRefresh = () => {
        setRefreshing(true)
        setRefreshKey(prev => prev + 1)
        setTimeout(() => {
            setLastUpdated(new Date())
            setRefreshing(false)
        }, 1000)
    }

    const [activeTab, setActiveTab] = useState("current") // Add state for tabs

    return (
        <Card className="w-full">
            <CardHeader className="pb-2">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <CardTitle className="text-xl flex items-center gap-2">
                            <TrendingUp className="h-5 w-5 text-primary" />
                            Market Price Trends
                        </CardTitle>
                        <CardDescription>
                            Real-time commodity prices and market analysis
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        {mounted && <span className="hidden sm:inline">Updated: {lastUpdated.toLocaleTimeString()}</span>}
                        <Button variant="ghost" size="icon" onClick={handleRefresh} disabled={refreshing}>
                            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
                    <TabsList>
                        <TabsTrigger value="current">Current Prices</TabsTrigger>
                        <TabsTrigger value="historical">Historical Trends</TabsTrigger>
                        <TabsTrigger value="movers">Top Movers</TabsTrigger>
                    </TabsList>

                    <TabsContent value="current" key={`current-${refreshKey}`}>
                        <CurrentPricesTab />
                    </TabsContent>

                    <TabsContent value="historical" key={`hist-${refreshKey}`}>
                        <HistoricalTrendsTab />
                    </TabsContent>

                    <TabsContent value="movers" key={`movers-${refreshKey}`}>
                        <TopMoversTab />
                    </TabsContent>
                </Tabs>
            </CardContent>
        </Card>
    )
}
