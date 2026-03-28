"use client"

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
    Search,
    Loader2,
    TrendingUp,
    TrendingDown,
    Package,
    Leaf,
    Grid3X3,
    List,
    ChevronRight,
} from 'lucide-react'
import { AppLayout } from "@/components/layout/AppLayout"
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { commoditiesService, CommodityFilters } from '@/services/commodities'
import { CommodityWithPrice, CommoditiesWithPriceResponse } from '@/types'

// Icon mapping for commodity categories
const categoryIcons: { [key: string]: string } = {
    'Grains': '🌾',
    'Vegetables': '🥬',
    'Fruits': '🍎',
    'Spices': '🌶️',
    'Cash Crops': '🌿',
    'Uncategorized': '📦',
}

// Icon mapping for specific commodities
const commodityIcons: { [key: string]: string } = {
    'rice': '🌾',
    'wheat': '🌾',
    'tomato': '🍅',
    'onion': '🧅',
    'potato': '🥔',
    'banana': '🍌',
    'coconut': '🥥',
    'cardamom': '🌿',
    'pepper': '🌶️',
    'rubber': '🌳',
}

function getCommodityIcon(name: string, category: string): string {
    return commodityIcons[name.toLowerCase()] || categoryIcons[category] || '🌱'
}

export default function CommoditiesPage() {
    const router = useRouter()
    const searchParams = useSearchParams()
    
    // Initialize state from URL parameters
    const [commodities, setCommodities] = useState<CommodityWithPrice[]>([])
    const [categories, setCategories] = useState<string[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchQuery, setSearchQuery] = useState('')
    const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
    const [selectedForCompare, setSelectedForCompare] = useState<string[]>([])  
    const [trendFilter, setTrendFilter] = useState<'rising' | 'falling' | 'stable' | null>(null)
    const [seasonFilter, setSeasonFilter] = useState<boolean | null>(null)
    const [minPrice, setMinPrice] = useState<number | undefined>(undefined)
    const [maxPrice, setMaxPrice] = useState<number | undefined>(undefined)
    const [sortBy, setSortBy] = useState<'name' | 'price' | 'change'>(
        (searchParams.get('sortBy') as 'name' | 'price' | 'change') || 'name'
    )
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(
        (searchParams.get('sortOrder') as 'asc' | 'desc') || 'asc'
    )
    const [totalCount, setTotalCount] = useState(0)
    const [displayCount, setDisplayCount] = useState(10)

    // Fetch commodities with filters
    const fetchCommodities = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            const filters: CommodityFilters = {
                search: searchQuery || undefined,
                categories: selectedCategory ? [selectedCategory] : undefined,
                trend: trendFilter || undefined,
                inSeason: seasonFilter ?? undefined,
                minPrice: minPrice,
                maxPrice: maxPrice,
                sortBy: sortBy,
                sortOrder: sortOrder,
                limit: 50, // Paginated - load more on demand
            }

            const response = await commoditiesService.getWithPrices(filters)
            setCommodities(response.commodities)
            setTotalCount(response.total)
        } catch (err: any) {
            console.error('Failed to fetch commodities:', err)
            setError('Failed to load commodities. Please try again.')
        } finally {
            setLoading(false)
        }
    }, [searchQuery, selectedCategory, trendFilter, seasonFilter, minPrice, maxPrice, sortBy, sortOrder])

    // Fetch categories on mount
    useEffect(() => {
        async function fetchCategories() {
            try {
                const cats = await commoditiesService.getCategories()
                setCategories(cats)
            } catch (err) {
                console.error('Failed to fetch categories:', err)
            }
        }
        fetchCategories()
    }, [])

    // Fetch commodities when filters change
    useEffect(() => {
        const debounce = setTimeout(() => {
            fetchCommodities()
            setDisplayCount(10) // Reset to show 10 items when filters change
        }, 300)
        return () => clearTimeout(debounce)
    }, [fetchCommodities])

    const handleCommodityClick = (commodity: CommodityWithPrice) => {
        router.push(`/commodities/${commodity.id}`)
    }

    // Toggle compare selection
    const toggleCompareSelection = (commodityId: string) => {
        setSelectedForCompare(prev => {
            if (prev.includes(commodityId)) {
                return prev.filter(id => id !== commodityId)
            }
            if (prev.length >= 5) {
                return prev // Max 5 items
            }
            return [...prev, commodityId]
        })
    }

    // Clear all filters
    const clearFilters = () => {
        setSearchQuery('')
        setSelectedCategory(null)
        setTrendFilter(null)
        setSeasonFilter(null)
        setMinPrice(undefined)
        setMaxPrice(undefined)
        setSortBy('name')
        setSortOrder('asc')
    }

    // Check if any filters are active
    const hasActiveFilters = selectedCategory !== null || trendFilter !== null || seasonFilter !== null || minPrice !== undefined || maxPrice !== undefined

    // Filter commodities based on client-side search
    const filteredCommodities = useMemo(() => {
        return commodities.filter(commodity => {
            const matchesSearch = searchQuery === '' ||
                commodity.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (commodity.name_local && commodity.name_local.toLowerCase().includes(searchQuery.toLowerCase()))
            return matchesSearch
        })
    }, [commodities, searchQuery])

    return (
        <AppLayout>
            <div className="min-h-screen bg-background">
                {/* Header */}
                <div className="bg-card border-b border-border sticky top-0 z-10">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                            <div>
                                <h1 className="text-2xl sm:text-3xl font-bold text-foreground flex items-center gap-2">
                                    <Leaf className="h-7 w-7 text-primary" />
                                    Commodities
                                </h1>
                                <p className="text-muted-foreground mt-1">
                                    Browse agricultural commodities across India
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge variant="secondary" className="text-sm">
                                    {filteredCommodities.length} of {totalCount} total
                                </Badge>
                            </div>
                        </div>

                        {/* Search and Filters */}
                        <div className="mt-6 flex flex-col sm:flex-row gap-4">
                            {/* Search */}
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <input
                                    type="text"
                                    placeholder="Search commodities..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2.5 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                />
                            </div>

                            {/* View Toggle */}
                            <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
                                <Button
                                    variant={viewMode === 'grid' ? 'default' : 'ghost'}
                                    size="sm"
                                    onClick={() => setViewMode('grid')}
                                    className="h-8 w-8 p-0"
                                >
                                    <Grid3X3 className="h-4 w-4" />
                                </Button>
                                <Button
                                    variant={viewMode === 'list' ? 'default' : 'ghost'}
                                    size="sm"
                                    onClick={() => setViewMode('list')}
                                    className="h-8 w-8 p-0"
                                >
                                    <List className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>

                        {/* Category Filters */}
                        <div className="mt-4 flex flex-wrap gap-2">
                            <Button
                                variant={selectedCategory === null ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => setSelectedCategory(null)}
                                className="rounded-full"
                            >
                                All
                            </Button>
                            {categories.map(category => (
                                <Button
                                    key={category}
                                    variant={selectedCategory === category ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => setSelectedCategory(category)}
                                    className="rounded-full"
                                >
                                    {categoryIcons[category] || '📦'} {category}
                                </Button>
                            ))}
                        </div>

                        {/* Advanced Filters */}
                        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                            {/* Sort By */}
                            <div className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-muted-foreground">Sort By</label>
                                <select
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value as 'name' | 'price' | 'change')}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                >
                                    <option value="name">Name</option>
                                    <option value="price">Price</option>
                                    <option value="change">Price Change</option>
                                </select>
                            </div>

                            {/* Sort Order */}
                            <div className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-muted-foreground">Order</label>
                                <select
                                    value={sortOrder}
                                    onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                >
                                    <option value="asc">Ascending</option>
                                    <option value="desc">Descending</option>
                                </select>
                            </div>

                            {/* Min Price */}
                            <div className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-muted-foreground">Min Price (₹)</label>
                                <input
                                    type="number"
                                    placeholder="0"
                                    value={minPrice ?? ''}
                                    onChange={(e) => setMinPrice(e.target.value ? Number(e.target.value) : undefined)}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                />
                            </div>

                            {/* Max Price */}
                            <div className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-muted-foreground">Max Price (₹)</label>
                                <input
                                    type="number"
                                    placeholder="No limit"
                                    value={maxPrice ?? ''}
                                    onChange={(e) => setMaxPrice(e.target.value ? Number(e.target.value) : undefined)}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                />
                            </div>
                        </div>

                        {/* Clear Filters Button */}
                        {hasActiveFilters && (
                            <div className="mt-3">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={clearFilters}
                                    className="text-xs"
                                >
                                    Clear all filters
                                </Button>
                            </div>
                        )}
                    </div>
                </div>

                {/* Content */}
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    {/* Loading State */}
                    {loading && (
                        <div className="flex flex-col items-center justify-center py-20">
                            <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
                            <p className="text-muted-foreground">Loading commodities...</p>
                        </div>
                    )}

                    {/* Error State */}
                    {error && !loading && (
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="bg-destructive/10 text-destructive rounded-lg p-6 text-center max-w-md">
                                <Package className="h-10 w-10 mx-auto mb-4" />
                                <p className="font-medium">{error}</p>
                                <Button
                                    variant="outline"
                                    className="mt-4"
                                    onClick={() => window.location.reload()}
                                >
                                    Try Again
                                </Button>
                            </div>
                        </div>
                    )}

                    {/* Empty State */}
                    {!loading && !error && filteredCommodities.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="bg-muted rounded-lg p-8 text-center max-w-md">
                                <Search className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
                                <p className="font-medium text-foreground">No commodities found</p>
                                <p className="text-sm text-muted-foreground mt-2">
                                    {searchQuery
                                        ? `No results for "${searchQuery}"`
                                        : 'No commodities in this category'}
                                </p>
                                {(searchQuery || selectedCategory) && (
                                    <Button
                                        variant="outline"
                                        className="mt-4"
                                        onClick={() => {
                                            setSearchQuery('')
                                            setSelectedCategory(null)
                                        }}
                                    >
                                        Clear Filters
                                    </Button>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Grid View */}
                    {!loading && !error && filteredCommodities.length > 0 && viewMode === 'grid' && (
                        <>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
                                {filteredCommodities.slice(0, displayCount).map((commodity) => (
                                <Card
                                    key={commodity.id}
                                    className="group cursor-pointer hover:shadow-lg hover:border-primary/50 transition-all duration-200 overflow-hidden"
                                    onClick={() => handleCommodityClick(commodity)}
                                >
                                    <CardContent className="p-0">
                                        {/* Icon Section */}
                                        <div className="bg-gradient-to-br from-primary/10 to-primary/5 p-6 text-center">
                                            <span className="text-5xl">
                                                {getCommodityIcon(commodity.name, commodity.category || 'Uncategorized')}
                                            </span>
                                        </div>

                                        {/* Info Section */}
                                        <div className="p-4">
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="min-w-0">
                                                    <h3 className="font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                                                        {commodity.name}
                                                    </h3>
                                                    {commodity.name_local && (
                                                        <p className="text-xs text-muted-foreground truncate">
                                                            {commodity.name_local}
                                                        </p>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <Badge variant="secondary" className="shrink-0 text-xs">
                                                        {commodity.unit}
                                                    </Badge>
                                                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                                </div>
                                            </div>

                                            <div className="mt-3 flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                                                        {commodity.category || 'Uncategorized'}
                                                    </span>
                                                    {commodity.is_in_season && (
                                                        <Badge variant="outline" className="text-xs text-green-600 border-green-300">
                                                            In Season
                                                        </Badge>
                                                    )}
                                                </div>

                                                {commodity.current_price && (
                                                    <div className="text-right">
                                                        <div className="flex items-center justify-end gap-2 mb-0.5">
                                                            {commodity.last_updated === new Date().toISOString().split('T')[0] && (
                                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 text-green-600 border-green-600 bg-green-50">
                                                                    Live
                                                                </Badge>
                                                            )}
                                                            <p className="font-semibold text-sm">
                                                                ₹{commodity.current_price.toLocaleString()}
                                                            </p>
                                                        </div>
                                                        {commodity.price_change_1d !== undefined && (
                                                            <p className={`text-xs flex items-center justify-end gap-0.5 ${(commodity.price_change_1d || 0) >= 0
                                                                ? 'text-green-600'
                                                                : 'text-red-600'
                                                                }`}>
                                                                {(commodity.price_change_1d || 0) >= 0 ? (
                                                                    <TrendingUp className="h-3 w-3" />
                                                                ) : (
                                                                    <TrendingDown className="h-3 w-3" />
                                                                )}
                                                                {(commodity.price_change_1d || 0) >= 0 ? '+' : ''}
                                                                {(commodity.price_change_1d || 0).toFixed(1)}%
                                                            </p>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                        {displayCount < filteredCommodities.length && (
                            <div className="flex justify-center mt-8">
                                <Button
                                    onClick={() => setDisplayCount(prev => prev + 10)}
                                    variant="outline"
                                    className="gap-2"
                                >
                                    <Package className="h-4 w-4" />
                                    Load More ({filteredCommodities.length - displayCount} remaining)
                                </Button>
                            </div>
                        )}
                        </>
                    )}

                    {/* List View */}
                    {!loading && !error && filteredCommodities.length > 0 && viewMode === 'list' && (
                        <>
                            <div className="space-y-2">
                                {filteredCommodities.slice(0, displayCount).map((commodity) => (
                                <Card
                                    key={commodity.id}
                                    className="group cursor-pointer hover:shadow-md hover:border-primary/50 transition-all duration-200"
                                    onClick={() => handleCommodityClick(commodity)}
                                >
                                    <CardContent className="p-4">
                                        <div className="flex items-center gap-4">
                                            {/* Icon */}
                                            <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center shrink-0">
                                                <span className="text-2xl">
                                                    {getCommodityIcon(commodity.name, commodity.category || 'Uncategorized')}
                                                </span>
                                            </div>

                                            {/* Info */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                                                        {commodity.name}
                                                    </h3>
                                                    <Badge variant="secondary" className="text-xs">
                                                        {commodity.unit}
                                                    </Badge>
                                                    {commodity.is_in_season && (
                                                        <Badge variant="outline" className="text-xs text-green-600 border-green-300">
                                                            In Season
                                                        </Badge>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <span className="text-xs text-muted-foreground">
                                                        {commodity.category || 'Uncategorized'}
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Price */}
                                            {commodity.current_price && (
                                                <div className="text-right shrink-0">
                                                    <div className="flex items-center justify-end gap-2 mb-0.5">
                                                        {commodity.last_updated === new Date().toISOString().split('T')[0] && (
                                                            <Badge variant="outline" className="text-[10px] h-5 px-1.5 text-green-600 border-green-600 bg-green-50">
                                                                Live
                                                            </Badge>
                                                        )}
                                                        <p className="font-semibold">
                                                            ₹{commodity.current_price.toLocaleString()}
                                                        </p>
                                                    </div>
                                                    {commodity.price_change_1d !== undefined && (
                                                        <p className={`text-xs flex items-center justify-end gap-0.5 ${(commodity.price_change_1d || 0) >= 0
                                                            ? 'text-green-600'
                                                            : 'text-red-600'
                                                            }`}>
                                                            {(commodity.price_change_1d || 0) >= 0 ? (
                                                                <TrendingUp className="h-3 w-3" />
                                                            ) : (
                                                                <TrendingDown className="h-3 w-3" />
                                                            )}
                                                            {(commodity.price_change_1d || 0) >= 0 ? '+' : ''}
                                                            {(commodity.price_change_1d || 0).toFixed(1)}%
                                                        </p>
                                                    )}
                                                </div>
                                            )}

                                            {/* Arrow */}
                                            <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                        {displayCount < filteredCommodities.length && (
                            <div className="flex justify-center mt-8">
                                <Button
                                    onClick={() => setDisplayCount(prev => prev + 10)}
                                    variant="outline"
                                    className="gap-2"
                                >
                                    <Package className="h-4 w-4" />
                                    Load More ({filteredCommodities.length - displayCount} remaining)
                                </Button>
                            </div>
                        )}
                        </>
                    )}
                </div>
            </div>
        </AppLayout>
    )
}
