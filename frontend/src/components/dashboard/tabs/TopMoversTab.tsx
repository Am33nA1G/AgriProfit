"use client"

import React, { useState, useEffect } from "react"
import { TrendingUp, TrendingDown, ArrowRight } from "lucide-react"
import { pricesService, TopMover } from "@/services/prices"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function TopMoversTab() {
    const [data, setData] = useState<{ gainers: TopMover[]; losers: TopMover[] } | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchMovers = async () => {
            setLoading(true)
            try {
                const result = await pricesService.getTopMovers()
                setData(result)
            } catch (error) {
                console.error(error)
            } finally {
                setLoading(false)
            }
        }
        fetchMovers()
    }, [])

    if (loading) {
        return (
            <div className="grid md:grid-cols-2 gap-4">
                {[1, 2].map((i) => (
                    <div key={i} className="space-y-3">
                        <Skeleton className="h-8 w-1/3 mb-4" />
                        {[1, 2, 3, 4, 5].map((j) => (
                            <Skeleton key={j} className="h-12 w-full" />
                        ))}
                    </div>
                ))}
            </div>
        )
    }

    if (!data) return <div className="text-center py-8 text-muted-foreground">Unable to load top movers</div>

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Gainers */}
            <Card className="border-green-100 bg-green-50/10 dark:bg-green-900/10 dark:border-green-900">
                <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold flex items-center gap-2 text-green-700 dark:text-green-500">
                        <TrendingUp className="h-5 w-5" />
                        Biggest Gainers
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                    {data.gainers.map((item, i) => (
                        <div key={i} className="flex items-center justify-between p-2 rounded hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors">
                            <div className="flex flex-col">
                                <span className="font-medium">{item.commodity}</span>
                                <span className="text-xs text-muted-foreground">₹{item.price.toFixed(2)}/kg</span>
                            </div>
                            <div className="flex items-center gap-1 text-green-600 font-bold">
                                <span>+{item.change_percent}%</span>
                                <TrendingUp className="h-4 w-4" />
                            </div>
                        </div>
                    ))}
                </CardContent>
            </Card>

            {/* Losers */}
            <Card className="border-red-100 bg-red-50/10 dark:bg-red-900/10 dark:border-red-900">
                <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold flex items-center gap-2 text-red-700 dark:text-red-500">
                        <TrendingDown className="h-5 w-5" />
                        Biggest Losers
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                    {data.losers.map((item, i) => (
                        <div key={i} className="flex items-center justify-between p-2 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                            <div className="flex flex-col">
                                <span className="font-medium">{item.commodity}</span>
                                <span className="text-xs text-muted-foreground">₹{item.price.toFixed(2)}/kg</span>
                            </div>
                            <div className="flex items-center gap-1 text-red-600 font-bold">
                                <span>{item.change_percent}%</span>
                                <TrendingDown className="h-4 w-4" />
                            </div>
                        </div>
                    ))}
                </CardContent>
            </Card>
        </div>
    )
}
