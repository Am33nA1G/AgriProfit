"use client"

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import {
    Search,
    Loader2,
    Store,
    MapPin,
    Building2,
    Grid3X3,
    List,
    ChevronRight,
    X,
    Scale,
    Warehouse,
    Truck,
    Snowflake,
    Clock
} from 'lucide-react'
import { AppLayout } from "@/components/layout/AppLayout"
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { mandisService, MandiFilters } from '@/services/mandis'
import { MandiWithDistance, MandiDetail, MandisWithFiltersResponse } from '@/types'

// District colors for visual distinction
const districtColors: { [key: string]: string } = {
    'Thiruvananthapuram': 'bg-blue-100 text-blue-800',
    'Ernakulam': 'bg-green-100 text-green-800',
    'Kozhikode': 'bg-purple-100 text-purple-800',
    'Thrissur': 'bg-orange-100 text-orange-800',
    'Palakkad': 'bg-pink-100 text-pink-800',
    'Kannur': 'bg-yellow-100 text-yellow-800',
    'Kollam': 'bg-indigo-100 text-indigo-800',
    'Alappuzha': 'bg-cyan-100 text-cyan-800',
    'Kottayam': 'bg-teal-100 text-teal-800',
    'Idukki': 'bg-emerald-100 text-emerald-800',
    'Wayanad': 'bg-lime-100 text-lime-800',
    'Malappuram': 'bg-amber-100 text-amber-800',
}

function getDistrictColor(district: string): string {
    return districtColors[district] || 'bg-gray-100 text-gray-800'
}

export default function MandisPage() {
    const router = useRouter()
    const [mandis, setMandis] = useState<MandiWithDistance[]>([])
    const [states, setStates] = useState<string[]>([])
    const [districts, setDistricts] = useState<string[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchQuery, setSearchQuery] = useState('')
    const [selectedState, setSelectedState] = useState<string | null>(null)
    const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null)
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
    const [facilityFilter, setFacilityFilter] = useState<'weighbridge' | 'storage' | 'loading_dock' | 'cold_storage' | null>(null)
    const [totalCount, setTotalCount] = useState(0)
    const [sortBy, setSortBy] = useState<'name'>('name')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
    const [currentLimit, setCurrentLimit] = useState(50)
    const isInitialLoad = useRef(true)

    // Fetch mandis with filters
    const fetchMandis = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            const filters: MandiFilters = {
                search: searchQuery || undefined,
                states: selectedState ? [selectedState] : undefined,
                district: selectedDistrict || undefined,
                hasFacility: facilityFilter || undefined,
                sortBy: sortBy,
                sortOrder: sortOrder,
                limit: currentLimit,
            }

            const response = await mandisService.getWithFilters(filters)
            setMandis(response.mandis)
            setTotalCount(response.total)
        } catch (err: any) {
            console.error('Failed to fetch mandis:', err)
            setError('Failed to load mandis. Please try again.')
        } finally {
            setLoading(false)
        }
    }, [searchQuery, selectedState, selectedDistrict, facilityFilter, sortBy, sortOrder, currentLimit])

    // On mount: fetch states
    useEffect(() => {
        async function initPage() {
            try {
                const stateList = await mandisService.getStates()
                setStates(stateList)
            } catch (err) {
                console.error('Failed to fetch states:', err)
            }
        }
        initPage()
    }, [])

    // Fetch districts when state changes
    useEffect(() => {
        if (selectedState) {
            mandisService.getDistrictsByState(selectedState)
                .then(setDistricts)
                .catch(() => setDistricts([]))
        } else {
            setDistricts([])
        }
        setSelectedDistrict(null) // Reset district when state changes
    }, [selectedState])

    // Fetch mandis when filters change — skip debounce on initial load
    useEffect(() => {
        setCurrentLimit(50) // Reset to initial limit when filters change

        if (isInitialLoad.current) {
            isInitialLoad.current = false
            fetchMandis()
            return
        }

        const debounce = setTimeout(() => {
            fetchMandis()
        }, 300)
        return () => clearTimeout(debounce)
    }, [fetchMandis])

    // Handle mandi click - navigate to detail page
    const handleMandiClick = (mandi: MandiWithDistance) => {
        router.push(`/mandis/${mandi.id}`)
    }

    // Clear all filters
    const clearFilters = () => {
        setSearchQuery('')
        setSelectedState(null)
        setSelectedDistrict(null)
        setFacilityFilter(null)
        setSortBy('name')
        setSortOrder('asc')
        setCurrentLimit(50)
    }

    // Load more mandis
    const loadMore = () => {
        setCurrentLimit(prev => prev + 100)
    }

    // Check if any filters are active
    const hasActiveFilters = selectedState !== null || selectedDistrict !== null || facilityFilter !== null

    // Filter mandis based on client-side search
    const filteredMandis = useMemo(() => {
        return mandis.filter(mandi => {
            const matchesSearch = searchQuery === '' ||
                mandi.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                mandi.district.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (mandi.address && mandi.address.toLowerCase().includes(searchQuery.toLowerCase()))
            return matchesSearch
        })
    }, [mandis, searchQuery])

    return (
        <AppLayout>
            <div className="min-h-screen bg-background">
                {/* Header */}
                <div className="bg-card border-b border-border sticky top-0 z-10">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                            <div>
                                <h1 className="text-2xl sm:text-3xl font-bold text-foreground flex items-center gap-2">
                                    <Store className="h-7 w-7 text-primary" />
                                    Mandis
                                </h1>
                                <p className="text-muted-foreground mt-1">
                                    Agricultural markets across India
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge variant="secondary" className="text-sm">
                                    {filteredMandis.length} of {totalCount} total
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
                                    placeholder="Search mandis by name, district..."
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

                        {/* State Filters */}
                        <div className="mt-4 flex flex-wrap gap-2">
                            <Button
                                variant={selectedState === null ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => setSelectedState(null)}
                                className="rounded-full"
                            >
                                All States
                            </Button>
                            {states.map(state => (
                                <Button
                                    key={state}
                                    variant={selectedState === state ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => setSelectedState(state)}
                                    className="rounded-full"
                                >
                                    {state}
                                </Button>
                            ))}
                        </div>

                        {/* District Filters (shown when state selected) */}
                        {districts.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-2">
                                <Button
                                    variant={selectedDistrict === null ? 'secondary' : 'outline'}
                                    size="sm"
                                    onClick={() => setSelectedDistrict(null)}
                                    className="rounded-full"
                                >
                                    All Districts
                                </Button>
                                {districts.map(district => (
                                    <Button
                                        key={district}
                                        variant={selectedDistrict === district ? 'secondary' : 'outline'}
                                        size="sm"
                                        onClick={() => setSelectedDistrict(district)}
                                        className="rounded-full"
                                    >
                                        {district}
                                    </Button>
                                ))}
                            </div>
                        )}

                        {/* Advanced Filters */}
                        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {/* Sort Order */}
                            <div className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-muted-foreground">Order</label>
                                <select
                                    value={sortOrder}
                                    onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                >
                                    <option value="asc">A to Z</option>
                                    <option value="desc">Z to A</option>
                                </select>
                            </div>

                            {/* Facility Filter */}
                            <div className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-muted-foreground">Facility</label>
                                <select
                                    value={facilityFilter || ''}
                                    onChange={(e) => setFacilityFilter(e.target.value as any || null)}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                >
                                    <option value="">All Facilities</option>
                                    <option value="weighbridge">⚖️ Weighbridge</option>
                                    <option value="storage">🏪 Storage</option>
                                    <option value="loading_dock">🚚 Loading Dock</option>
                                    <option value="cold_storage">❄️ Cold Storage</option>
                                </select>
                            </div>
                        </div>

                        {/* Clear Filters */}
                        {hasActiveFilters && (
                            <div className="mt-3 flex items-center justify-end">
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
                            <p className="text-muted-foreground">Loading mandis...</p>
                        </div>
                    )}

                    {/* Error State */}
                    {error && !loading && (
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="bg-destructive/10 text-destructive rounded-lg p-6 text-center max-w-md">
                                <Store className="h-10 w-10 mx-auto mb-4" />
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
                    {!loading && !error && filteredMandis.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="bg-muted rounded-lg p-8 text-center max-w-md">
                                <Search className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
                                <p className="font-medium text-foreground">No mandis found</p>
                                <p className="text-sm text-muted-foreground mt-2">
                                    {searchQuery
                                        ? `No results for "${searchQuery}"`
                                        : 'No mandis in this district'}
                                </p>
                                {(searchQuery || selectedDistrict) && (
                                    <Button
                                        variant="outline"
                                        className="mt-4"
                                        onClick={() => {
                                            setSearchQuery('')
                                            setSelectedDistrict(null)
                                        }}
                                    >
                                        Clear Filters
                                    </Button>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Grid View */}
                    {!loading && !error && filteredMandis.length > 0 && viewMode === 'grid' && (
                        <>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
                                {filteredMandis.map((mandi) => (
                                <Card
                                    key={mandi.id}
                                    className="group cursor-pointer hover:shadow-lg hover:border-primary/50 transition-all duration-200 overflow-hidden"
                                    onClick={() => handleMandiClick(mandi)}
                                >
                                    <CardContent className="p-0">
                                        {/* Icon Section */}
                                        <div className="bg-gradient-to-br from-primary/10 to-primary/5 p-6 text-center">
                                            <Store className="h-12 w-12 mx-auto text-primary" />
                                        </div>

                                        {/* Info Section */}
                                        <div className="p-4">
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="min-w-0">
                                                    <h3 className="font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                                                        {mandi.name}
                                                    </h3>
                                                    {mandi.market_code && (
                                                        <p className="text-xs text-muted-foreground">
                                                            Code: {mandi.market_code}
                                                        </p>
                                                    )}
                                                    {mandi.top_prices && mandi.top_prices.some(p => p.as_of === new Date().toISOString().split('T')[0]) && (
                                                        <Badge variant="outline" className="text-[10px] h-5 px-1.5 text-green-600 border-green-600 bg-green-50 shrink-0">
                                                            Live
                                                        </Badge>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="mt-3 flex flex-wrap items-center gap-2">
                                                <Badge className={`text-xs ${getDistrictColor(mandi.district)}`}>
                                                    <MapPin className="h-3 w-3 mr-1" />
                                                    {mandi.district}
                                                </Badge>
                                                <Badge variant="outline" className="text-xs">
                                                    {mandi.state}
                                                </Badge>

                                            </div>

                                            {/* Facilities */}
                                            <div className="mt-2 flex flex-wrap gap-1">
                                                {mandi.facilities?.weighbridge && (
                                                    <Badge variant="outline" className="text-[10px] py-0">
                                                        <Scale className="h-2.5 w-2.5 mr-0.5" /> Scale
                                                    </Badge>
                                                )}
                                                {mandi.facilities?.storage && (
                                                    <Badge variant="outline" className="text-[10px] py-0">
                                                        <Warehouse className="h-2.5 w-2.5 mr-0.5" /> Storage
                                                    </Badge>
                                                )}
                                                {mandi.facilities?.cold_storage && (
                                                    <Badge variant="outline" className="text-[10px] py-0">
                                                        <Snowflake className="h-2.5 w-2.5 mr-0.5" /> Cold
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                            </div>

                            {/* Load More Button */}
                            {mandis.length < totalCount && (
                                <div className="flex justify-center mt-8">
                                    <Button
                                        onClick={loadMore}
                                        variant="outline"
                                        size="lg"
                                        className="min-w-[200px]"
                                    >
                                        Load More ({mandis.length} of {totalCount})
                                    </Button>
                                </div>
                            )}
                        </>
                    )}

                    {/* List View */}
                    {!loading && !error && filteredMandis.length > 0 && viewMode === 'list' && (
                        <>
                            <div className="space-y-2">
                                {filteredMandis.map((mandi) => (
                                <Card
                                    key={mandi.id}
                                    className="group cursor-pointer hover:shadow-md hover:border-primary/50 transition-all duration-200"
                                    onClick={() => handleMandiClick(mandi)}
                                >
                                    <CardContent className="p-4">
                                        <div className="flex items-center gap-4">
                                            {/* Icon */}
                                            <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center shrink-0">
                                                <Store className="h-6 w-6 text-primary" />
                                            </div>

                                            {/* Info */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                                                        {mandi.name}
                                                    </h3>
                                                    {mandi.market_code && (
                                                        <Badge variant="outline" className="text-xs">
                                                            {mandi.market_code}
                                                        </Badge>
                                                    )}
                                                    {mandi.top_prices && mandi.top_prices.some(p => p.as_of === new Date().toISOString().split('T')[0]) && (
                                                        <Badge variant="outline" className="text-[10px] h-5 px-1.5 text-green-600 border-green-600 bg-green-50">
                                                            Live
                                                        </Badge>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2 mt-1 flex-wrap">
                                                    <Badge className={`text-xs ${getDistrictColor(mandi.district)}`}>
                                                        <MapPin className="h-3 w-3 mr-1" />
                                                        {mandi.district}
                                                    </Badge>
                                                    <span className="text-xs text-muted-foreground">
                                                        {mandi.state}
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Address */}
                                            {mandi.address && (
                                                <div className="hidden md:block text-right shrink-0 max-w-xs">
                                                    <p className="text-xs text-muted-foreground truncate">
                                                        {mandi.address}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Arrow */}
                                            <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                            </div>

                            {/* Load More Button */}
                            {mandis.length < totalCount && (
                                <div className="flex justify-center mt-8">
                                    <Button
                                        onClick={loadMore}
                                        variant="outline"
                                        size="lg"
                                        className="min-w-[200px]"
                                    >
                                        Load More ({mandis.length} of {totalCount})
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
