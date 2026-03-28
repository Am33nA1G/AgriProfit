"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
    Loader2,
    AlertTriangle,
    BarChart3,
    Info,
} from "lucide-react"
import { forecastService, type ForecastResponse } from "@/services/forecast"
import ForecastChart from "@/components/ForecastChart"
import DirectionHeroCard from "@/components/DirectionHeroCard"
import PriceRangeBar from "@/components/PriceRangeBar"
import { AppLayout } from "@/components/layout/AppLayout"

function slugToLabel(slug: string): string {
    return slug.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}


const CONFIDENCE_CONFIG = {
    Green: {
        label: "Reliable",
        className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
        warning: null as string | null,
    },
    Yellow: {
        label: "Directional only",
        className: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
        warning: null as string | null,
    },
    Red: {
        label: "Low Confidence",
        className: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
        warning: "This commodity has high price volatility or limited market data. The forecast direction may be unreliable — do not use for financial decisions." as string | null,
    },
}


export default function ForecastPage() {
    const [commodity, setCommodity] = useState("")
    const [state, setState] = useState("")
    const [district, setDistrict] = useState("")

    // 1. All v5 commodities
    const { data: allSlugs = [], isLoading: allSlugsLoading } = useQuery<string[]>({
        queryKey: ["forecast-commodities"],
        queryFn: () => forecastService.getCommodities(),
        staleTime: 60 * 60 * 1000,
    })

    // 2. States that have v5 data for the selected commodity
    const { data: stateOptions = [], isLoading: statesLoading } = useQuery<string[]>({
        queryKey: ["forecast-states", commodity],
        queryFn: () => forecastService.getStatesForCommodity(commodity),
        enabled: !!commodity,
        staleTime: 60 * 60 * 1000,
    })

    // 3. Districts in selected state for selected commodity
    const { data: districtOptions = [], isLoading: districtsLoading } = useQuery<string[]>({
        queryKey: ["forecast-districts", commodity, state],
        queryFn: () => forecastService.getDistrictsForCommodityState(commodity, state),
        enabled: !!(commodity && state),
        staleTime: 60 * 60 * 1000,
    })

    const canFetch = commodity && district

    const {
        data: forecast,
        isLoading,
        isError,
        error,
    } = useQuery<ForecastResponse>({
        queryKey: ["forecast", commodity, district],
        queryFn: () => forecastService.getForecast(commodity, district, 7),
        enabled: !!canFetch,
        staleTime: 5 * 60 * 1000,
        retry: 1,
    })

    const confConfig = forecast ? CONFIDENCE_CONFIG[forecast.confidence_colour] : null

    return (
        <AppLayout>
        <div className="min-h-screen bg-background p-4 lg:p-8">
            <div className="container mx-auto max-w-5xl">

                {/* ---- Header ---- */}
                <div className="mb-8" id="forecast-header">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-500/20">
                            <BarChart3 className="h-6 w-6 text-violet-500" />
                        </div>
                        <h1 className="text-2xl lg:text-3xl font-bold tracking-tight">
                            Price Forecast
                        </h1>
                    </div>
                    <p className="text-muted-foreground text-sm lg:text-base max-w-2xl">
                        ML-powered price predictions for agricultural commodities.
                        Select a commodity, state, and district to see the forecast.
                    </p>
                </div>

                {/* ---- Selectors ---- */}
                <div className="flex flex-wrap gap-3 mb-8" id="forecast-selectors">
                    {/* Commodity — v5 only */}
                    <select
                        id="commodity-select"
                        value={commodity}
                        onChange={(e) => {
                            setCommodity(e.target.value)
                            setState("")
                            setDistrict("")
                        }}
                        disabled={allSlugsLoading}
                        className="h-10 px-3 rounded-lg border border-border bg-background text-sm focus:ring-2 focus:ring-violet-500 focus:outline-none min-w-[180px] disabled:opacity-50"
                    >
                        <option value="">{allSlugsLoading ? "Loading..." : "Select Commodity"}</option>
                        {allSlugs.map((slug) => (
                            <option key={slug} value={slug}>{slugToLabel(slug)}</option>
                        ))}
                    </select>

                    {/* State — only states with v5 data for selected commodity */}
                    <select
                        id="state-select"
                        value={state}
                        onChange={(e) => {
                            setState(e.target.value)
                            setDistrict("")
                        }}
                        disabled={!commodity || statesLoading}
                        className="h-10 px-3 rounded-lg border border-border bg-background text-sm focus:ring-2 focus:ring-violet-500 focus:outline-none min-w-[180px] disabled:opacity-50"
                    >
                        <option value="">
                            {!commodity ? "Select Commodity first" : statesLoading ? "Loading..." : "Select State"}
                        </option>
                        {stateOptions.map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>

                    {/* District — only districts with v5 data for selected commodity+state */}
                    <select
                        id="district-select"
                        value={district}
                        onChange={(e) => setDistrict(e.target.value)}
                        disabled={!state || districtsLoading}
                        className="h-10 px-3 rounded-lg border border-border bg-background text-sm focus:ring-2 focus:ring-violet-500 focus:outline-none min-w-[180px] disabled:opacity-50"
                    >
                        <option value="">
                            {!state ? "Select State first" : districtsLoading ? "Loading..." : "Select District"}
                        </option>
                        {districtOptions.map((d) => (
                            <option key={d} value={d}>{d}</option>
                        ))}
                    </select>

                </div>

                {/* ---- Empty state ---- */}
                {!canFetch && (
                    <div className="flex flex-col items-center justify-center py-20 text-center" id="forecast-empty">
                        <BarChart3 className="h-12 w-12 text-muted-foreground/40 mb-4" />
                        <h2 className="text-lg font-medium text-muted-foreground mb-2">
                            Select a commodity and district
                        </h2>
                        <p className="text-sm text-muted-foreground/70 max-w-md">
                            Choose a commodity, state, and district to view the price forecast
                            with predicted direction, price range, and confidence level.
                        </p>
                    </div>
                )}

                {/* ---- Loading ---- */}
                {canFetch && isLoading && (
                    <div className="flex flex-col items-center justify-center py-20" id="forecast-loading">
                        <Loader2 className="h-8 w-8 text-violet-500 animate-spin mb-4" />
                        <p className="text-sm text-muted-foreground">Generating forecast...</p>
                    </div>
                )}

                {/* ---- Error ---- */}
                {canFetch && isError && (() => {
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    const status = (error as any)?.response?.status
                    const msg = status === 404
                        ? "No forecast data is available for this combination. Try selecting a different district."
                        : "Something went wrong loading the forecast. Please try again."
                    return (
                        <div className="flex flex-col items-center justify-center py-20 text-center" id="forecast-error">
                            <AlertTriangle className="h-8 w-8 text-amber-400 mb-4" />
                            <p className="text-sm text-muted-foreground max-w-sm">{msg}</p>
                        </div>
                    )
                })()}

                {/* ---- Forecast Result ---- */}
                {canFetch && forecast && (
                    <div className="space-y-6" id="forecast-result">

                        {/* Fallback Banner (UI-05) — show when tier_label is seasonal average fallback */}
                        {forecast.tier_label === "seasonal average fallback" && (
                            <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800" id="fallback-banner">
                                <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
                                <div>
                                    <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                                        Limited Data Coverage
                                    </p>
                                    <p className="text-sm text-amber-700 dark:text-amber-400 mt-1">
                                        {forecast.coverage_message ?? "Insufficient price history. Showing seasonal averages."}
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Stale data banner — PROD-05 */}
                        {forecast.is_stale && (
                            <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800" id="stale-data-banner" data-testid="stale-data-banner">
                                <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
                                <p className="text-sm text-amber-700 dark:text-amber-400">
                                    Price data last updated {forecast.data_freshness_days} day{forecast.data_freshness_days !== 1 ? "s" : ""} ago — live market feed may be unavailable. Forecast is based on the most recent data we have.
                                </p>
                            </div>
                        )}

                        {/* Red confidence warning banner */}
                        {confConfig?.warning && (
                            <div className="flex items-start gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800" id="low-confidence-banner">
                                <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
                                <div>
                                    <p className="text-sm font-medium text-red-800 dark:text-red-300">
                                        Unreliable Forecast
                                        {forecast.mape_pct != null && (
                                            <span className="font-normal"> — typical error ±{forecast.mape_pct.toFixed(0)}%</span>
                                        )}
                                    </p>
                                    <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                                        {confConfig.warning}
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Direction Hero Card */}
                        <DirectionHeroCard
                            direction={forecast.direction}
                            confidence_colour={forecast.confidence_colour}
                            horizon_days={forecast.horizon_days}
                            mape_pct={forecast.mape_pct}
                            model_version={forecast.model_version ?? null}
                            r2_score={forecast.r2_score}
                        />

                        {/* Price Range */}
                        <PriceRangeBar
                            price_low={forecast.price_low}
                            price_mid={forecast.price_mid}
                            price_high={forecast.price_high}
                        />

                        {/* Chart */}
                        {forecast.forecast_points && forecast.forecast_points.length > 0 && forecast.confidence_colour !== 'Red' && (
                            <div className="p-5 rounded-xl bg-card border border-border/50 shadow-sm">
                                <ForecastChart
                                    forecastPoints={forecast.forecast_points}
                                    confidenceColour={forecast.confidence_colour}
                                    commodity={forecast.commodity}
                                />
                            </div>
                        )}

                        {/* Note when chart is hidden for Red confidence */}
                        {forecast.confidence_colour === 'Red' && (
                            <p className="text-xs text-muted-foreground/60 text-center py-2">
                                Chart unavailable for low-confidence forecasts
                            </p>
                        )}

                        {/* Data freshness and farmer metadata — PROD-05 */}
                        <div className="flex items-start gap-2 text-xs text-muted-foreground/70 pt-2" id="data-freshness">
                            <Info className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                            <div>
                                {forecast.n_markets > 0 && (
                                    <p>
                                        Based on data from {forecast.n_markets} markets.
                                        {forecast.typical_error_inr != null && (
                                            <> Typical forecast error: ₹{forecast.typical_error_inr}/quintal.</>
                                        )}
                                    </p>
                                )}
                                <p>
                                    Last data: {forecast.last_data_date}. Forecasts are directional signals, not precise predictions. Actual prices may vary.
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
        </AppLayout>
    )
}
