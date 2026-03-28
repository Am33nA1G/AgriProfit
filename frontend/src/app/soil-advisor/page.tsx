"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Loader2, Leaf, FlaskConical, AlertTriangle } from "lucide-react"
import { AppLayout } from "@/components/layout/AppLayout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
    soilAdvisorApi,
    type NutrientDistribution,
    type CropRecommendation,
    type FertiliserAdvice,
    type SoilAdvisorResponse,
} from "@/services/soil-advisor"

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Mandatory disclaimer — always rendered above crop list, no dismiss button. */
function SoilDisclaimer({ disclaimer }: { disclaimer: string }) {
    return (
        <div
            className="border border-amber-200 bg-amber-50 rounded-md p-4 mb-4"
            role="note"
            aria-label="soil-disclaimer"
        >
            <p className="text-sm text-amber-800 font-medium">{disclaimer}</p>
        </div>
    )
}

/** CSS-based horizontal bar showing high/medium/low percentages for one nutrient. */
function NutrientBar({ nd }: { nd: NutrientDistribution }) {
    return (
        <div className="mb-3">
            <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">{nd.nutrient}</span>
            </div>
            <div className="flex h-6 w-full rounded overflow-hidden text-xs font-medium">
                {nd.high_pct > 0 && (
                    <div
                        className="flex items-center justify-center bg-green-500 text-white"
                        style={{ width: `${nd.high_pct}%` }}
                    >
                        {nd.high_pct}%
                    </div>
                )}
                {nd.medium_pct > 0 && (
                    <div
                        className="flex items-center justify-center bg-amber-400 text-white"
                        style={{ width: `${nd.medium_pct}%` }}
                    >
                        {nd.medium_pct}%
                    </div>
                )}
                {nd.low_pct > 0 && (
                    <div
                        className="flex items-center justify-center bg-red-500 text-white"
                        style={{ width: `${nd.low_pct}%` }}
                    >
                        {nd.low_pct}%
                    </div>
                )}
            </div>
            <div className="flex gap-3 mt-1 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                    <span className="inline-block w-2 h-2 rounded-sm bg-green-500" />
                    High
                </span>
                <span className="flex items-center gap-1">
                    <span className="inline-block w-2 h-2 rounded-sm bg-amber-400" />
                    Medium
                </span>
                <span className="flex items-center gap-1">
                    <span className="inline-block w-2 h-2 rounded-sm bg-red-500" />
                    Low
                </span>
            </div>
        </div>
    )
}

function demandBadgeClass(demand: string | null): string {
    if (demand === "HIGH") return "bg-green-100 text-green-800"
    if (demand === "MEDIUM") return "bg-amber-100 text-amber-800"
    if (demand === "LOW") return "bg-gray-100 text-gray-600"
    return ""
}

/** Ranked crop recommendation row. */
function CropRow({ crop }: { crop: CropRecommendation }) {
    return (
        <div className="flex items-center justify-between py-2 border-b last:border-b-0">
            <div className="flex items-center gap-2">
                <span className="w-6 h-6 flex items-center justify-center rounded-full bg-green-600 text-white text-xs font-bold">
                    {crop.suitability_rank}
                </span>
                <span className="font-medium text-gray-800">{crop.crop_name}</span>
            </div>
            <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">
                    Score: {crop.suitability_score.toFixed(2)}
                </span>
                {crop.seasonal_demand && (
                    <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${demandBadgeClass(
                            crop.seasonal_demand
                        )}`}
                    >
                        {crop.seasonal_demand}
                    </span>
                )}
            </div>
        </div>
    )
}

/** Fertiliser advice card for one deficient nutrient. */
function FertiliserCard({ advice }: { advice: FertiliserAdvice }) {
    return (
        <div className="border border-blue-200 rounded-md p-3 mb-2 bg-blue-50">
            <div className="flex items-center gap-1 mb-1">
                <FlaskConical className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-semibold text-blue-800">{advice.nutrient}</span>
            </div>
            <p className="text-xs text-blue-700 mb-1">{advice.message}</p>
            <p className="text-xs text-gray-600">{advice.fertiliser_recommendation}</p>
        </div>
    )
}

/** Coverage gap banner shown when a state returns 404 with coverage_gap=true. */
function CoverageGapBanner({ message }: { message: string }) {
    return (
        <div className="border border-yellow-300 bg-yellow-50 rounded-md p-4 mt-4">
            <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-700" />
                <p className="text-yellow-800 text-sm">
                    Soil data is not available for this region. {message}
                </p>
            </div>
        </div>
    )
}

/** Results panel showing disclaimer, nutrient bars, crops, and fertiliser advice. */
function ResultsPanel({ profile }: { profile: SoilAdvisorResponse }) {
    return (
        <div>
            {/* Disclaimer ALWAYS first — no dismiss button */}
            <SoilDisclaimer disclaimer={profile.disclaimer} />

            {/* NPK/pH Distribution Bars */}
            <Card className="mb-4">
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Nutrient Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                    {profile.nutrient_distributions.map((nd) => (
                        <NutrientBar key={nd.nutrient} nd={nd} />
                    ))}
                </CardContent>
            </Card>

            {/* Crop Recommendations */}
            <Card className="mb-4">
                <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-1">
                        <Leaf className="h-4 w-4 text-green-600" />
                        Crop Recommendations
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {profile.crop_recommendations.map((crop) => (
                        <CropRow key={crop.crop_name} crop={crop} />
                    ))}
                </CardContent>
            </Card>

            {/* Fertiliser Advice */}
            {profile.fertiliser_advice.length > 0 && (
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center gap-1">
                            <FlaskConical className="h-4 w-4 text-blue-600" />
                            Fertiliser Advice
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {profile.fertiliser_advice.map((advice) => (
                            <FertiliserCard key={advice.nutrient} advice={advice} />
                        ))}
                    </CardContent>
                </Card>
            )}
        </div>
    )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function SoilAdvisorPage() {
    const [selectedState, setSelectedState] = useState<string>("")
    const [selectedDistrict, setSelectedDistrict] = useState<string>("")
    const [selectedBlock, setSelectedBlock] = useState<string>("")

    // States list — fetched on mount
    const { data: states = [], isLoading: statesLoading } = useQuery({
        queryKey: ["soil-advisor-states"],
        queryFn: soilAdvisorApi.getStates,
    })

    // Districts — enabled only when state is selected
    const {
        data: districts = [],
        isLoading: districtsLoading,
    } = useQuery({
        queryKey: ["soil-advisor-districts", selectedState],
        queryFn: () => soilAdvisorApi.getDistricts(selectedState),
        enabled: !!selectedState,
    })

    // Blocks — enabled only when district is selected
    const {
        data: blocks = [],
        isLoading: blocksLoading,
    } = useQuery({
        queryKey: ["soil-advisor-blocks", selectedState, selectedDistrict],
        queryFn: () => soilAdvisorApi.getBlocks(selectedState, selectedDistrict),
        enabled: !!selectedState && !!selectedDistrict,
    })

    // Profile — enabled only when all three are selected
    const {
        data: profile,
        isLoading: profileLoading,
        error: profileError,
    } = useQuery({
        queryKey: ["soil-advisor-profile", selectedState, selectedDistrict, selectedBlock],
        queryFn: () => soilAdvisorApi.getProfile(selectedState, selectedDistrict, selectedBlock),
        enabled: !!selectedState && !!selectedDistrict && !!selectedBlock,
        retry: false,
    })

    // Detect coverage gap from API error
    const coverageGapError = (profileError as any)?.response?.data?.detail?.coverage_gap === true
    const coverageGapMessage = (profileError as any)?.response?.data?.detail?.message ?? ""

    function handleStateChange(e: React.ChangeEvent<HTMLSelectElement>) {
        setSelectedState(e.target.value)
        setSelectedDistrict("")
        setSelectedBlock("")
    }

    function handleDistrictChange(e: React.ChangeEvent<HTMLSelectElement>) {
        setSelectedDistrict(e.target.value)
        setSelectedBlock("")
    }

    function handleBlockChange(e: React.ChangeEvent<HTMLSelectElement>) {
        setSelectedBlock(e.target.value)
    }

    return (
        <AppLayout>
            <div className="max-w-2xl mx-auto px-4 py-6">
                {/* Page Header */}
                <div className="mb-6">
                    <h1 className="text-2xl font-bold text-gray-900">Soil Crop Advisor</h1>
                    <p className="text-sm text-gray-500 mt-1">
                        Available for 21 states — block-level soil health data
                    </p>
                </div>

                {/* Drill-down Selectors */}
                <Card className="mb-6">
                    <CardContent className="pt-4 space-y-4">
                        {/* State Selector */}
                        <div>
                            <label
                                htmlFor="state-select"
                                className="block text-sm font-medium text-gray-700 mb-1"
                            >
                                State
                            </label>
                            {statesLoading ? (
                                <div className="flex items-center gap-2 text-sm text-gray-500">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Loading states...
                                </div>
                            ) : (
                                <select
                                    id="state-select"
                                    aria-label="State"
                                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                                    value={selectedState}
                                    onChange={handleStateChange}
                                >
                                    <option value="">Select a state</option>
                                    {states.map((s) => (
                                        <option key={s} value={s}>
                                            {s}
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>

                        {/* District Selector — disabled until state selected */}
                        <div>
                            <label
                                htmlFor="district-select"
                                className="block text-sm font-medium text-gray-700 mb-1"
                            >
                                District
                            </label>
                            {districtsLoading ? (
                                <div className="flex items-center gap-2 text-sm text-gray-500">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Loading districts...
                                </div>
                            ) : (
                                <select
                                    id="district-select"
                                    aria-label="District"
                                    data-testid="district-select"
                                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                                    value={selectedDistrict}
                                    onChange={handleDistrictChange}
                                    disabled={!selectedState}
                                >
                                    <option value="">
                                        {selectedState ? "Select a district" : "Select a state first"}
                                    </option>
                                    {districts.map((d) => (
                                        <option key={d} value={d}>
                                            {d}
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>

                        {/* Block Selector — disabled until district selected */}
                        <div>
                            <label
                                htmlFor="block-select"
                                className="block text-sm font-medium text-gray-700 mb-1"
                            >
                                Block
                            </label>
                            {blocksLoading ? (
                                <div className="flex items-center gap-2 text-sm text-gray-500">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Loading blocks...
                                </div>
                            ) : (
                                <select
                                    id="block-select"
                                    aria-label="Block"
                                    data-testid="block-select"
                                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                                    value={selectedBlock}
                                    onChange={handleBlockChange}
                                    disabled={!selectedDistrict}
                                >
                                    <option value="">
                                        {selectedDistrict ? "Select a block" : "Select a district first"}
                                    </option>
                                    {blocks.map((b) => (
                                        <option key={b} value={b}>
                                            {b}
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Coverage Gap Banner */}
                {coverageGapError && (
                    <CoverageGapBanner message={coverageGapMessage} />
                )}

                {/* Profile Loading Spinner */}
                {profileLoading && (
                    <div className="flex items-center justify-center py-8 gap-2 text-gray-500">
                        <Loader2 className="h-5 w-5 animate-spin" />
                        <span className="text-sm">Loading soil profile...</span>
                    </div>
                )}

                {/* Results Panel */}
                {profile && !profileLoading && !coverageGapError && (
                    <ResultsPanel profile={profile} />
                )}
            </div>
        </AppLayout>
    )
}
