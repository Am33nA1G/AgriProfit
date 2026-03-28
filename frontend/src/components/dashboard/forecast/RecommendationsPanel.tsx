"use client"

import React from "react"
import { ForecastSummary } from "@/services/forecasts"
import { Lightbulb, TrendingUp, Calendar, AlertCircle } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

interface RecommendationsPanelProps {
    summary: ForecastSummary
}

export function RecommendationsPanel({ summary }: RecommendationsPanelProps) {
    return (
        <div className="grid gap-4 sm:grid-cols-3">
            <Alert className="bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800 pl-12">
                <TrendingUp className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <AlertTitle className="text-blue-800 dark:text-blue-300">Trend</AlertTitle>
                <AlertDescription className="text-blue-700 dark:text-blue-400 mt-1">
                    Prices are expected to be <strong>{summary.trend}</strong> over the selected period.
                </AlertDescription>
            </Alert>

            <Alert className="bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800 pl-12">
                <Calendar className="h-4 w-4 text-green-600 dark:text-green-400" />
                <AlertTitle className="text-green-800 dark:text-green-300">Best Time to Sell</AlertTitle>
                <AlertDescription className="text-green-700 dark:text-green-400 mt-1">
                    Target window: <strong>{new Date(summary.best_sell_window[0]).toLocaleDateString([], { month: 'short', day: 'numeric' })} - {new Date(summary.best_sell_window[1]).toLocaleDateString([], { month: 'short', day: 'numeric' })}</strong>
                </AlertDescription>
            </Alert>

            <Alert className="bg-purple-50 border-purple-200 dark:bg-purple-900/20 dark:border-purple-800 pl-12">
                <Lightbulb className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                <AlertTitle className="text-purple-800 dark:text-purple-300">Peak Prediction</AlertTitle>
                <AlertDescription className="text-purple-700 dark:text-purple-400 mt-1">
                    Expected peak of <strong>₹{summary.peak_price.toFixed(2)}</strong> on {new Date(summary.peak_date).toLocaleDateString()}.
                </AlertDescription>
            </Alert>
        </div>
    )
}
