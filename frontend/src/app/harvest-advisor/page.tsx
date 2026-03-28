"use client"

import { useState, useEffect, useCallback } from 'react'
import { Loader2 } from 'lucide-react'
import { AppLayout } from "@/components/layout/AppLayout"
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'
import {
    getRecommendation,
    getHarvestAdvisorDistricts,
    HarvestAdvisorResponse,
    CropRecommendation,
    WeatherWarning,
} from '@/services/harvest-advisor'

const SEASONS = [
    { value: 'kharif', label: 'Kharif (Jun-Oct)' },
    { value: 'rabi', label: 'Rabi (Nov-Apr)' },
    { value: 'zaid', label: 'Zaid (Apr-Jun)' },
    { value: 'annual', label: 'Annual (All Year)' },
]

function getRankBadgeClass(rank: number): string {
    switch (rank) {
        case 1: return 'bg-yellow-400 text-black'
        case 2: return 'bg-gray-300 text-black'
        case 3: return 'bg-amber-600 text-white'
        default: return 'bg-gray-100 text-gray-800'
    }
}

function getWarningClass(severity: string): string {
    switch (severity) {
        case 'high':
        case 'extreme':
            return 'bg-red-50 border-l-4 border-red-500'
        case 'medium':
            return 'bg-amber-50 border-l-4 border-amber-500'
        default:
            return 'bg-green-50 border-l-4 border-green-500'
    }
}

function getDroughtBadge(risk: string | null | undefined): { className: string; label: string } {
    switch (risk) {
        case 'extreme': return { className: 'bg-red-900 text-white', label: 'Extreme' }
        case 'high': return { className: 'bg-red-600 text-white', label: 'High' }
        case 'medium': return { className: 'bg-amber-500 text-white', label: 'Medium' }
        case 'low': return { className: 'bg-yellow-400 text-black', label: 'Low' }
        default: return { className: 'bg-green-500 text-white', label: 'None' }
    }
}

function PriceDirection({ direction }: { direction: string }) {
    switch (direction) {
        case 'up': return <span className="text-green-600 font-semibold">&#8593; Up</span>
        case 'down': return <span className="text-red-600 font-semibold">&#8595; Down</span>
        default: return <span className="text-gray-500 font-semibold">&#8594; Flat</span>
    }
}

function ConfidenceBadge({ colour }: { colour: string }) {
    const cls = colour === 'Green'
        ? 'bg-green-100 text-green-800'
        : colour === 'Yellow'
            ? 'bg-yellow-100 text-yellow-800'
            : 'bg-red-100 text-red-800'
    return <Badge className={cls}>{colour}</Badge>
}

export default function HarvestAdvisorPage() {
    const [states, setStates] = useState<string[]>([])
    const [districts, setDistricts] = useState<string[]>([])
    const [selectedState, setSelectedState] = useState('')
    const [selectedDistrict, setSelectedDistrict] = useState('')
    const [selectedSeason, setSelectedSeason] = useState('kharif')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [result, setResult] = useState<HarvestAdvisorResponse | null>(null)

    // Fetch states on mount
    useEffect(() => {
        api.get<string[]>('/soil-advisor/states')
            .then(r => setStates(r.data))
            .catch(() => setStates([]))
    }, [])

    // Fetch districts when state changes
    useEffect(() => {
        setSelectedDistrict('')
        if (selectedState) {
            getHarvestAdvisorDistricts(selectedState)
                .then(setDistricts)
                .catch(() => setDistricts([]))
        } else {
            setDistricts([])
        }
    }, [selectedState])

    const handleGetRecommendation = useCallback(async () => {
        if (!selectedState || !selectedDistrict) return
        setLoading(true)
        setError(null)
        setResult(null)
        const data = await getRecommendation(selectedState, selectedDistrict, selectedSeason)
        if (data) {
            setResult(data)
        } else {
            setError('Failed to get recommendations. Please try again.')
        }
        setLoading(false)
    }, [selectedState, selectedDistrict, selectedSeason])

    return (
        <AppLayout>
            <div className="min-h-screen bg-background">
                {/* Header */}
                <div className="bg-card border-b border-border">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                        <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
                            Harvest Advisor
                        </h1>
                        <p className="text-muted-foreground mt-1">
                            Get crop recommendations based on soil, weather, and market data
                        </p>

                        {/* Selectors */}
                        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="flex flex-col gap-1">
                                <label htmlFor="state-select" className="text-xs font-medium text-muted-foreground">State</label>
                                <select
                                    id="state-select"
                                    value={selectedState}
                                    onChange={e => setSelectedState(e.target.value)}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                >
                                    <option value="">Select State</option>
                                    {states.map(s => (
                                        <option key={s} value={s}>{s}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="flex flex-col gap-1">
                                <label htmlFor="district-select" className="text-xs font-medium text-muted-foreground">District</label>
                                <select
                                    id="district-select"
                                    value={selectedDistrict}
                                    onChange={e => setSelectedDistrict(e.target.value)}
                                    disabled={!selectedState}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm disabled:opacity-50"
                                >
                                    <option value="">Select District</option>
                                    {districts.map(d => (
                                        <option key={d} value={d}>{d}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="flex flex-col gap-1">
                                <label htmlFor="season-select" className="text-xs font-medium text-muted-foreground">Season</label>
                                <select
                                    id="season-select"
                                    value={selectedSeason}
                                    onChange={e => setSelectedSeason(e.target.value)}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                >
                                    {SEASONS.map(s => (
                                        <option key={s.value} value={s.value}>{s.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div className="mt-4">
                            <Button
                                onClick={handleGetRecommendation}
                                disabled={!selectedState || !selectedDistrict || loading}
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                        Loading...
                                    </>
                                ) : (
                                    'Get Recommendations'
                                )}
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    {/* Loading State */}
                    {loading && (
                        <div className="flex flex-col items-center justify-center py-20">
                            <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
                            <p className="text-muted-foreground">Analysing data...</p>
                        </div>
                    )}

                    {/* Error State */}
                    {error && !loading && (
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="bg-destructive/10 text-destructive rounded-lg p-6 text-center max-w-md">
                                <p className="font-medium">{error}</p>
                            </div>
                        </div>
                    )}

                    {/* Results */}
                    {result && !loading && (
                        <div className="space-y-6">
                            {/* Weather Warnings */}
                            {result.weather_warnings.length > 0 && (
                                <div className="space-y-3">
                                    <h2 className="text-lg font-semibold text-foreground">Weather Warnings</h2>
                                    {result.weather_warnings.map((w, idx) => (
                                        <div key={idx} className={`p-4 rounded-lg ${getWarningClass(w.severity)}`}>
                                            <div className="flex items-start gap-3">
                                                <div className="min-w-0">
                                                    <p className="font-semibold capitalize">{w.warning_type.replace('_', ' ')}</p>
                                                    <p className="text-sm mt-1">{w.message}</p>
                                                    <p className="text-sm mt-1 text-gray-600">{w.crop_impact}</p>
                                                    <p className="text-xs mt-1 text-gray-500">{w.affected_period}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Drought Risk Badge */}
                            {result.drought_risk && (
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-medium text-muted-foreground">Drought Risk:</span>
                                    <Badge className={getDroughtBadge(result.drought_risk).className}>
                                        {getDroughtBadge(result.drought_risk).label}
                                    </Badge>
                                </div>
                            )}

                            {/* Crop Recommendations */}
                            {result.recommendations.length > 0 ? (
                                <div className="space-y-4">
                                    <h2 className="text-lg font-semibold text-foreground">Top Crop Recommendations</h2>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {result.recommendations.map(rec => (
                                            <Card key={rec.rank} className="overflow-hidden">
                                                <CardContent className="p-4">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <Badge className={getRankBadgeClass(rec.rank)}>
                                                            #{rec.rank}
                                                        </Badge>
                                                        <ConfidenceBadge colour={rec.price_confidence_colour} />
                                                    </div>

                                                    <h3 className="font-semibold text-lg">{rec.crop_name}</h3>

                                                    {/* Net profit hero */}
                                                    <div className="mt-2">
                                                        <p className={`font-bold text-lg ${rec.expected_profit_per_ha >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                                                            {rec.expected_profit_per_ha >= 0 ? '' : '–'}&#8377;{Math.abs(rec.expected_profit_per_ha).toLocaleString('en-IN')}/ha
                                                        </p>
                                                        <p className="text-xs text-muted-foreground">Net profit (after input costs)</p>
                                                    </div>

                                                    {/* Cost breakdown */}
                                                    <div className="mt-2 space-y-0.5 text-xs text-muted-foreground border-t border-border pt-2">
                                                        <p className="flex justify-between">
                                                            <span>Gross Revenue</span>
                                                            <span>&#8377;{rec.gross_revenue_per_ha.toLocaleString('en-IN')}</span>
                                                        </p>
                                                        <p className="flex justify-between text-red-500">
                                                            <span>Input Costs</span>
                                                            <span>–&#8377;{rec.input_cost_per_ha.toLocaleString('en-IN')}</span>
                                                        </p>
                                                    </div>

                                                    <div className="mt-2 space-y-1 text-sm text-muted-foreground">
                                                        <p>Yield: {rec.expected_yield_kg_ha.toLocaleString('en-IN')} kg/ha</p>
                                                        <p>Price: &#8377;{rec.expected_price_per_quintal.toLocaleString('en-IN')}/quintal</p>
                                                        <p>Direction: <PriceDirection direction={rec.price_direction} /></p>
                                                    </div>

                                                    <div className="mt-3 text-xs text-muted-foreground space-y-1">
                                                        <p>Sow: {rec.sowing_window}</p>
                                                        <p>Harvest: {rec.harvest_window}</p>
                                                    </div>

                                                    {rec.soil_suitability_note && (
                                                        <p className="mt-2 text-sm italic text-gray-600">
                                                            {rec.soil_suitability_note}
                                                        </p>
                                                    )}
                                                </CardContent>
                                            </Card>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center py-10">
                                    <p className="text-muted-foreground">No data available for this district</p>
                                </div>
                            )}

                            {/* Coverage Notes */}
                            {result.coverage_notes.length > 0 && (
                                <ul className="text-sm text-gray-500 list-disc pl-5 space-y-1">
                                    {result.coverage_notes.map((note, i) => (
                                        <li key={i}>{note}</li>
                                    ))}
                                </ul>
                            )}

                            {/* Disclaimer */}
                            <p className="italic text-gray-400 text-xs mt-4">
                                {result.disclaimer}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </AppLayout>
    )
}
