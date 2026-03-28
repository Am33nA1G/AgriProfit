'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
    ArrowLeft,
    TrendingUp,
    TrendingDown,
    MapPin,
    IndianRupee,
    Package,
    BarChart3,
    Loader2,
    AlertCircle,
    CheckCircle,
    ChevronDown,
    ChevronUp,
    Star,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { inventoryService, InventoryAnalysisResponse, CommodityAnalysis, MandiRecommendation } from '@/services/inventory';
import { AppLayout } from '@/components/layout/AppLayout';

function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0,
    }).format(amount);
}

function formatPrice(amount: number): string {
    return new Intl.NumberFormat('en-IN', {
        maximumFractionDigits: 2,
    }).format(amount);
}

function formatPricePerKg(amount: number): string {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(amount);
}

interface MandiCardProps {
    mandi: MandiRecommendation;
    rank: number;
    quantity: number;
    unit: string;
}

function MandiCard({ mandi, rank, quantity, unit }: MandiCardProps) {
    // Convert prices from per quintal to per kg (1 quintal = 100 kg)
    const pricePerKg = mandi.modal_price / 100;
    const minPricePerKg = mandi.min_price / 100;
    const maxPricePerKg = mandi.max_price / 100;
    const hasTransport = mandi.net_profit != null;

    const verdictColors: Record<string, string> = {
        excellent: 'bg-green-100 text-green-800 border-green-200',
        good: 'bg-blue-100 text-blue-800 border-blue-200',
        marginal: 'bg-yellow-100 text-yellow-800 border-yellow-200',
        not_viable: 'bg-red-100 text-red-800 border-red-200',
    };

    return (
        <div className={`flex items-start gap-4 p-4 rounded-lg border ${rank === 1 ? 'border-green-500 bg-green-50' : 'border-gray-200 bg-white'}`}>
            <div className={`flex items-center justify-center w-8 h-8 rounded-full ${rank === 1 ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-600'}`}>
                {rank === 1 ? <Star className="w-4 h-4" /> : rank}
            </div>
            <div className="flex-1">
                <div className="flex items-start justify-between">
                    <div>
                        <h4 className="font-semibold text-gray-900">{mandi.mandi_name}</h4>
                        <p className="text-sm text-gray-500 flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {mandi.district}, {mandi.state}
                            {mandi.is_local && (
                                <Badge variant="outline" className="ml-2 text-xs bg-blue-50 text-blue-600 border-blue-200">
                                    Local
                                </Badge>
                            )}
                            {mandi.verdict && (
                                <Badge variant="outline" className={`ml-2 text-xs ${verdictColors[mandi.verdict] || ''}`}>
                                    {mandi.verdict.replace('_', ' ')}
                                </Badge>
                            )}
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-lg font-bold text-green-600">
                            {formatPricePerKg(pricePerKg)}/kg
                        </p>
                        <p className="text-xs text-gray-500">
                            Range: {formatPricePerKg(minPricePerKg)} - {formatPricePerKg(maxPricePerKg)}
                        </p>
                    </div>
                </div>
                {hasTransport && (
                    <div className="mt-2 grid grid-cols-3 gap-2 text-sm">
                        {mandi.distance_km != null && (
                            <div className="px-2 py-1 bg-gray-50 rounded text-center">
                                <span className="text-gray-500 text-xs block">Distance</span>
                                <span className="font-medium">{Math.round(mandi.distance_km)} km</span>
                            </div>
                        )}
                        {mandi.transport_cost != null && (
                            <div className="px-2 py-1 bg-gray-50 rounded text-center">
                                <span className="text-gray-500 text-xs block">Transport Cost</span>
                                <span className="font-medium text-red-600">{formatCurrency(mandi.transport_cost)}</span>
                            </div>
                        )}
                        {mandi.net_profit != null && (
                            <div className="px-2 py-1 bg-gray-50 rounded text-center">
                                <span className="text-gray-500 text-xs block">Net Profit</span>
                                <span className={`font-medium ${mandi.net_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {formatCurrency(mandi.net_profit)}
                                </span>
                            </div>
                        )}
                    </div>
                )}
                <div className="mt-3 pt-3 border-t border-gray-100">
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">
                            {hasTransport ? 'Estimated net profit:' : `Estimated revenue for ${quantity} ${unit}:`}
                        </span>
                        <span className="font-semibold text-gray-900">
                            {formatCurrency(mandi.estimated_min_revenue)} - {formatCurrency(mandi.estimated_max_revenue)}
                        </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                        Price as of: {new Date(mandi.price_date).toLocaleDateString('en-IN')}
                    </p>
                </div>
            </div>
        </div>
    );
}

interface CommodityAnalysisCardProps {
    analysis: CommodityAnalysis;
}

function CommodityAnalysisCard({ analysis }: CommodityAnalysisCardProps) {
    const [expanded, setExpanded] = useState(false);
    const hasRecommendations = analysis.best_mandis && analysis.best_mandis.length > 0;

    return (
        <Card className="overflow-hidden">
            <CardHeader className="bg-gradient-to-r from-green-50 to-blue-50">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-white rounded-lg shadow-sm">
                            <Package className="w-6 h-6 text-green-600" />
                        </div>
                        <div>
                            <CardTitle className="text-xl">{analysis.commodity_name}</CardTitle>
                            <CardDescription>
                                {analysis.quantity} {analysis.unit} in inventory
                            </CardDescription>
                        </div>
                    </div>
                    {hasRecommendations && (
                        <div className="text-right">
                            <p className="text-sm text-gray-500">Estimated Revenue</p>
                            <p className="text-xl font-bold text-green-600">
                                {formatCurrency(analysis.estimated_min_revenue)} - {formatCurrency(analysis.estimated_max_revenue)}
                            </p>
                        </div>
                    )}
                </div>
            </CardHeader>
            <CardContent className="p-6">
                {hasRecommendations ? (
                    <>
                        <div className="mb-4 p-4 bg-green-50 rounded-lg border border-green-200">
                            <div className="flex items-center gap-2 text-green-700">
                                <CheckCircle className="w-5 h-5" />
                                <span className="font-medium">Best Recommendation:</span>
                            </div>
                            <p className="mt-1 text-lg font-semibold text-green-800">
                                Sell at <span className="text-green-600">{analysis.recommended_mandi}</span> for{' '}
                                {formatPricePerKg((analysis.recommended_price || 0) / 100)}/kg
                                {analysis.best_mandis[0]?.net_profit != null && (
                                    <span className="text-sm font-normal text-green-700">
                                        {' '}· Net profit: {formatCurrency(analysis.best_mandis[0].net_profit)}
                                    </span>
                                )}
                            </p>
                        </div>

                        <div className="space-y-3">
                            <MandiCard
                                mandi={analysis.best_mandis[0]}
                                rank={1}
                                quantity={analysis.quantity}
                                unit={analysis.unit}
                            />

                            {analysis.best_mandis.length > 1 && (
                                <>
                                    <Button
                                        variant="ghost"
                                        className="w-full text-gray-600"
                                        onClick={() => setExpanded(!expanded)}
                                    >
                                        {expanded ? (
                                            <>
                                                <ChevronUp className="w-4 h-4 mr-2" />
                                                Hide other options
                                            </>
                                        ) : (
                                            <>
                                                <ChevronDown className="w-4 h-4 mr-2" />
                                                Show {analysis.best_mandis.length - 1} more options
                                            </>
                                        )}
                                    </Button>

                                    {expanded && (
                                        <div className="space-y-3">
                                            {analysis.best_mandis.slice(1).map((mandi, index) => (
                                                <MandiCard
                                                    key={mandi.mandi_id}
                                                    mandi={mandi}
                                                    rank={index + 2}
                                                    quantity={analysis.quantity}
                                                    unit={analysis.unit}
                                                />
                                            ))}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="flex items-center gap-3 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                        <AlertCircle className="w-5 h-5 text-yellow-600" />
                        <div>
                            <p className="font-medium text-yellow-800">No price data available</p>
                            <p className="text-sm text-yellow-700">
                                {analysis.message || 'We don\'t have recent price data for this commodity.'}
                            </p>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

export default function AnalyzeInventoryPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [analysis, setAnalysis] = useState<InventoryAnalysisResponse | null>(null);

    useEffect(() => {
        async function fetchAnalysis() {
            // Check if user is logged in first
            if (typeof window !== 'undefined') {
                const token = localStorage.getItem('token');
                if (!token) {
                    router.push('/login');
                    return;
                }
            }

            try {
                setLoading(true);
                setError(null);
                const result = await inventoryService.analyzeInventory();
                setAnalysis(result);
            } catch (err: any) {
                console.error('Failed to analyze inventory:', err);
                if (err.response?.status === 401 || err.message === 'Network Error') {
                    router.push('/login');
                    return;
                }
                setError(err.response?.data?.detail || 'Failed to analyze inventory. Please try again.');
            } finally {
                setLoading(false);
            }
        }

        fetchAnalysis();
    }, [router]);

    return (
        <AppLayout>
            <div className="p-4 lg:p-8 max-w-6xl mx-auto">
                {/* Header */}
                <div className="flex items-center gap-4 mb-8">
                    <Button variant="ghost" size="icon" onClick={() => router.back()}>
                        <ArrowLeft className="w-5 h-5" />
                    </Button>
                    <div>
                        <h1 className="text-2xl lg:text-3xl font-bold text-gray-900">
                            Inventory Analysis
                        </h1>
                        <p className="text-gray-600">
                            Find the best mandis to sell your crops
                        </p>
                    </div>
                </div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20">
                        <Loader2 className="w-12 h-12 text-green-600 animate-spin mb-4" />
                        <p className="text-lg text-gray-600">Analyzing your inventory...</p>
                        <p className="text-sm text-gray-500">Finding the best prices across mandis</p>
                    </div>
                ) : error ? (
                    <Card className="border-red-200 bg-red-50">
                        <CardContent className="p-8 text-center">
                            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                            <h3 className="text-lg font-semibold text-red-800 mb-2">Analysis Failed</h3>
                            <p className="text-red-600 mb-4">{error}</p>
                            <Button onClick={() => window.location.reload()} variant="outline" className="border-red-300 text-red-600 hover:bg-red-100">
                                Try Again
                            </Button>
                        </CardContent>
                    </Card>
                ) : analysis && analysis.total_items === 0 ? (
                    <Card>
                        <CardContent className="p-8 text-center">
                            <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                            <h3 className="text-lg font-semibold text-gray-800 mb-2">No Inventory Found</h3>
                            <p className="text-gray-600 mb-4">
                                Add items to your inventory to get selling recommendations.
                            </p>
                            <Link href="/inventory">
                                <Button className="bg-green-600 hover:bg-green-700">
                                    Go to Inventory
                                </Button>
                            </Link>
                        </CardContent>
                    </Card>
                ) : analysis ? (
                    <>
                        {/* Summary Card */}
                        <Card className="mb-8 bg-gradient-to-r from-green-600 to-green-700 text-white">
                            <CardContent className="p-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-green-100 mb-1">Total Potential Revenue</p>
                                        <p className="text-3xl lg:text-4xl font-bold">
                                            {formatCurrency(analysis.total_estimated_min_revenue)} - {formatCurrency(analysis.total_estimated_max_revenue)}
                                        </p>
                                    </div>
                                    <div className="p-4 bg-white/20 rounded-xl">
                                        <BarChart3 className="w-8 h-8" />
                                    </div>
                                </div>
                                <div className="mt-4 pt-4 border-t border-green-500/50">
                                    <p className="text-green-100">
                                        Analyzing {analysis.total_items} item{analysis.total_items !== 1 ? 's' : ''} in your inventory
                                    </p>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Commodity Analysis Cards */}
                        <div className="space-y-6">
                            {analysis.analysis.map((item) => (
                                <CommodityAnalysisCard key={item.commodity_id} analysis={item} />
                            ))}
                        </div>

                        {/* Action Buttons */}
                        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
                            <Link href="/inventory">
                                <Button variant="outline" className="w-full sm:w-auto">
                                    <Package className="w-4 h-4 mr-2" />
                                    Update Inventory
                                </Button>
                            </Link>
                            <Link href="/sales">
                                <Button className="w-full sm:w-auto bg-green-600 hover:bg-green-700">
                                    <IndianRupee className="w-4 h-4 mr-2" />
                                    Record a Sale
                                </Button>
                            </Link>
                        </div>
                    </>
                ) : null}
            </div>
        </AppLayout>
    );
}
