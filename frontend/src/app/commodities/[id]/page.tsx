'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import {
    ArrowLeft,
    Calendar,
    MapPin,
    TrendingUp,
    TrendingDown,
} from 'lucide-react'
import { AppLayout } from '@/components/layout/AppLayout'

// Dynamic import recharts for code splitting
const ResponsiveContainer = dynamic(() => import('recharts').then(m => m.ResponsiveContainer), { ssr: false })
const LineChart = dynamic(() => import('recharts').then(m => m.LineChart), { ssr: false })
const Line = dynamic(() => import('recharts').then(m => m.Line), { ssr: false })
const XAxis = dynamic(() => import('recharts').then(m => m.XAxis), { ssr: false })
const YAxis = dynamic(() => import('recharts').then(m => m.YAxis), { ssr: false })
const CartesianGrid = dynamic(() => import('recharts').then(m => m.CartesianGrid), { ssr: false })
const Tooltip = dynamic(() => import('recharts').then(m => m.Tooltip), { ssr: false })
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { commoditiesService } from '@/services/commodities'
import type { CommodityDetail } from '@/types'

const MONTHS = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]

function formatMonthList(months?: number[]) {
    if (!months || months.length === 0) return 'N/A'
    return months
        .map((m) => MONTHS[m - 1] || '')
        .filter(Boolean)
        .join(', ')
}

export default function CommodityDetailPage() {
    const { id } = useParams<{ id: string }>()
    const router = useRouter()
    const [detail, setDetail] = useState<CommodityDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let mounted = true
        async function fetchDetail() {
            try {
                setLoading(true)
                setError(null)
                const data = await commoditiesService.getDetails(id)
                if (mounted) setDetail(data)
            } catch (err) {
                if (mounted) setError('Failed to load commodity details.')
            } finally {
                if (mounted) setLoading(false)
            }
        }
        if (id) fetchDetail()
        return () => { mounted = false }
    }, [id])

    const chartData = useMemo(() => {
        if (!detail?.price_history) return []
        // Get historical data (parquet) + recent data
        // Sort by date and format for chart
        return [...detail.price_history]
            .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
            .map((p) => ({
                date: new Date(p.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
                price: p.price,
            }))
    }, [detail])

    if (loading) {
        return (
            <AppLayout>
                <div className="p-6 md:p-8">
                    <div className="text-muted-foreground">Loading commodity details...</div>
                </div>
            </AppLayout>
        )
    }

    if (error || !detail) {
        return (
            <AppLayout>
                <div className="p-6 md:p-8">
                    <div className="text-destructive">{error || 'Not found'}</div>
                </div>
            </AppLayout>
        )
    }

    const isUp = (detail.price_changes?.['1d'] || 0) >= 0

    return (
        <AppLayout>
            <div className="p-6 md:p-8 space-y-6">
                <div className="flex items-center gap-3">
                    <Button variant="ghost" size="sm" onClick={() => router.push('/commodities')}>
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Back
                    </Button>
                    <div>
                        <h1 className="text-2xl md:text-3xl font-bold">{detail.name}</h1>
                        {detail.name_local && (
                            <p className="text-muted-foreground">{detail.name_local}</p>
                        )}
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Current Price</CardTitle>
                            <CardDescription>Average across all mandis</CardDescription>
                        </CardHeader>
                        <CardContent className="flex items-center justify-between">
                            <div className="text-2xl font-bold">₹{detail.current_price?.toLocaleString() ?? 'N/A'}</div>
                            <Badge variant="outline" className={isUp ? 'text-green-600 border-green-300' : 'text-red-600 border-red-300'}>
                                {isUp ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                                {detail.price_changes?.['1d']?.toFixed(1) ?? '0.0'}%
                            </Badge>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Seasonality</CardTitle>
                            <CardDescription>Growing & harvest months</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {detail.seasonal_info?.growing_months || detail.seasonal_info?.harvest_months ? (
                                <>
                                    <div className="text-sm">Growing: {formatMonthList(detail.seasonal_info?.growing_months)}</div>
                                    <div className="text-sm">Harvest: {formatMonthList(detail.seasonal_info?.harvest_months)}</div>
                                    {detail.seasonal_info?.is_in_season && (
                                        <Badge variant="outline" className="text-green-600 border-green-300">In Season</Badge>
                                    )}
                                </>
                            ) : (
                                <div className="text-sm text-muted-foreground">
                                    Seasonality data not available for this commodity
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Unit</CardTitle>
                            <CardDescription>Trading unit</CardDescription>
                        </CardHeader>
                        <CardContent className="text-xl font-semibold">{detail.unit || 'N/A'}</CardContent>
                    </Card>
                </div>

                <Card>
                    <CardHeader>
                        <CardTitle>Historical Prices & Trends</CardTitle>
                        <CardDescription>
                            {chartData.length > 0 ? `Last ${chartData.length} data points (Historical + Current)` : 'No data available'}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {chartData.length === 0 ? (
                            <p className="text-muted-foreground">No historical data available.</p>
                        ) : (
                            <div className="h-[320px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={chartData}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis 
                                            dataKey="date" 
                                            tick={{ fontSize: 12 }}
                                            interval={Math.floor(chartData.length / 10)}
                                        />
                                        <YAxis tick={{ fontSize: 12 }} />
                                        <Tooltip 
                                            contentStyle={{ fontSize: 12 }}
                                            formatter={(value: any) => [`₹${value.toLocaleString()}`, 'Price']}
                                        />
                                        <Line type="monotone" dataKey="price" stroke="#16a34a" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Top Mandis</CardTitle>
                            <CardDescription>Best prices currently</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {(detail.top_mandis || []).map((mandi) => (
                                <div key={`${mandi.name}-${mandi.as_of}`} className="flex items-center justify-between">
                                    <div className="text-sm">
                                        <div className="font-medium">{mandi.name}</div>
                                        <div className="text-muted-foreground flex items-center gap-1">
                                            <MapPin className="h-3 w-3" />
                                            {mandi.district || 'N/A'}
                                        </div>
                                    </div>
                                    <div className="font-semibold">₹{mandi.price.toLocaleString()}</div>
                                </div>
                            ))}
                            {(!detail.top_mandis || detail.top_mandis.length === 0) && (
                                <p className="text-muted-foreground">No mandi data available.</p>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Recent History</CardTitle>
                            <CardDescription>Daily average prices (all mandis)</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {(detail.price_history || []).slice(-10).reverse().map((point, idx) => {
                                const prevPoint = (detail.price_history || [])[detail.price_history.length - 11 + idx];
                                const change = prevPoint ? ((point.price - prevPoint.price) / prevPoint.price) * 100 : 0;
                                const isUp = change >= 0;
                                
                                return (
                                    <div key={point.date} className="flex items-center justify-between p-2 rounded hover:bg-gray-50 transition-colors">
                                        <div className="flex items-center gap-2">
                                            <Calendar className="h-3 w-3 text-gray-400" />
                                            <span className="text-sm font-medium">
                                                {new Date(point.date).toLocaleDateString('en-IN', { 
                                                    day: 'numeric', 
                                                    month: 'short',
                                                    year: 'numeric'
                                                })}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            {prevPoint && Math.abs(change) > 0.01 && (
                                                <span className={`text-xs ${isUp ? 'text-green-600' : 'text-red-600'}`}>
                                                    {isUp ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
                                                </span>
                                            )}
                                            <span className="font-semibold text-sm">₹{point.price.toLocaleString()}</span>
                                        </div>
                                    </div>
                                );
                            })}
                            {(!detail.price_history || detail.price_history.length === 0) && (
                                <p className="text-muted-foreground text-sm">No historical data available.</p>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </AppLayout>
    )
}
