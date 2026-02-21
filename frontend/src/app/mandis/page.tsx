"use client"

import { useState, useEffect, useCallback } from 'react'
import { useTranslations } from 'next-intl'
import { useRouter } from 'next/navigation'
import {
    Search,
    Loader2,
    Store,
    MapPin,
    Grid3X3,
    List,
    ChevronRight,
    Navigation,
    Scale,
    Warehouse,
    Truck,
    Snowflake,
    Filter,
    ArrowUpDown
} from 'lucide-react'
import { AppLayout } from "@/components/layout/AppLayout"
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { mandisService, MandiFilters } from '@/services/mandis'
import { authService } from '@/services/auth'
import { MandiWithDistance } from '@/types'

// Generate distinct colors from district name hash for visual variety
function getDistrictColor(district: string): string {
    const colors = [
        'bg-blue-100 text-blue-800',
        'bg-green-100 text-green-800',
        'bg-purple-100 text-purple-800',
        'bg-orange-100 text-orange-800',
        'bg-pink-100 text-pink-800',
        'bg-yellow-100 text-yellow-800',
        'bg-indigo-100 text-indigo-800',
        'bg-cyan-100 text-cyan-800',
        'bg-teal-100 text-teal-800',
        'bg-emerald-100 text-emerald-800',
        'bg-lime-100 text-lime-800',
        'bg-amber-100 text-amber-800',
    ]
    let hash = 0
    for (let i = 0; i < district.length; i++) {
        hash = district.charCodeAt(i) + ((hash << 5) - hash)
    }
    return colors[Math.abs(hash) % colors.length]
}

function FacilityBadges({ facilities }: { facilities: MandiWithDistance['facilities'] }) {
    if (!facilities) return null
    const hasSome = facilities.weighbridge || facilities.storage || facilities.loading_dock || facilities.cold_storage
    if (!hasSome) return null

    return (
        <div className="flex flex-wrap gap-1">
            {facilities.weighbridge && (
                <Badge variant="outline" className="text-[10px] py-0 bg-blue-50 text-blue-700 border-blue-200">
                    <Scale className="h-2.5 w-2.5 mr-0.5" /> Weighbridge
                </Badge>
            )}
            {facilities.storage && (
                <Badge variant="outline" className="text-[10px] py-0 bg-amber-50 text-amber-700 border-amber-200">
                    <Warehouse className="h-2.5 w-2.5 mr-0.5" /> Storage
                </Badge>
            )}
            {facilities.loading_dock && (
                <Badge variant="outline" className="text-[10px] py-0 bg-green-50 text-green-700 border-green-200">
                    <Truck className="h-2.5 w-2.5 mr-0.5" /> Loading
                </Badge>
            )}
            {facilities.cold_storage && (
                <Badge variant="outline" className="text-[10px] py-0 bg-cyan-50 text-cyan-700 border-cyan-200">
                    <Snowflake className="h-2.5 w-2.5 mr-0.5" /> Cold
                </Badge>
            )}
        </div>
    )
}

export default function MandisPage() {
    const t = useTranslations('mandis')
    const tc = useTranslations('common')
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
    const [userDistrict, setUserDistrict] = useState<string | null>(null)
    const [userState, setUserState] = useState<string | null>(null)
    const [facilityFilter, setFacilityFilter] = useState<'weighbridge' | 'storage' | 'loading_dock' | 'cold_storage' | null>(null)
    const [totalCount, setTotalCount] = useState(0)
    const [maxDistanceKm, setMaxDistanceKm] = useState<number | undefined>(undefined)
    const [sortBy, setSortBy] = useState<'name' | 'distance'>('name')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
    const [currentLimit, setCurrentLimit] = useState(50)

    // Fetch mandis with filters (search is server-side)
    const fetchMandis = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            const filters: MandiFilters = {
                search: searchQuery || undefined,
                states: selectedState ? [selectedState] : undefined,
                district: selectedDistrict || undefined,
                hasFacility: facilityFilter || undefined,
                userDistrict: userDistrict || undefined,
                userState: userState || undefined,
                maxDistanceKm: maxDistanceKm,
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
    }, [searchQuery, selectedState, selectedDistrict, facilityFilter, userDistrict, userState, maxDistanceKm, sortBy, sortOrder, currentLimit])

    // Fetch states on mount
    useEffect(() => {
        async function fetchStates() {
            try {
                const stateList = await mandisService.getStates()
                setStates(stateList)
            } catch (err) {
                console.error('Failed to fetch states:', err)
            }
        }
        fetchStates()

        // Fetch user district and state from auth
        async function fetchUserDistrict() {
            try {
                const user = await authService.getCurrentUser()
                if (user?.district) {
                    setUserDistrict(user.district)
                    setUserState(user.state || null)
                }
            } catch (err) {
                // User not logged in - show mandis without distance
            }
        }
        fetchUserDistrict()
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

    // Fetch mandis when filters change
    useEffect(() => {
        setCurrentLimit(50) // Reset to initial limit when filters change
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
        setMaxDistanceKm(undefined)
        setSortBy('name')
        setSortOrder('asc')
        setCurrentLimit(50)
    }

    // Load more mandis
    const loadMore = () => {
        setCurrentLimit(prev => prev + 100)
    }

    // Check if any filters are active
    const hasActiveFilters = selectedState !== null || selectedDistrict !== null ||
        facilityFilter !== null || maxDistanceKm !== undefined || searchQuery !== ''

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
                                    {t('title')}
                                </h1>
                                <p className="text-muted-foreground mt-1">
                                    {t('subtitle')}
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge variant="secondary" className="text-sm">
                                    {t('showing', { count: mandis.length, total: totalCount })}
                                </Badge>
                            </div>
                        </div>

                        {/* Search and View Toggle */}
                        <div className="mt-6 flex flex-col sm:flex-row gap-4">
                            {/* Search */}
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <input
                                    type="text"
                                    placeholder={t('search')}
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
                                {t('allStates')}
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
                                    {t('districts')}
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
                        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                            {/* Sort By */}
                            <div className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                                    <ArrowUpDown className="h-3 w-3" /> {tc('sortBy')}
                                </label>
                                <select
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value as 'name' | 'distance')}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                >
                                    <option value="name">{tc('name')}</option>
                                    <option value="distance" disabled={!userDistrict}>{t('distance')} {!userDistrict ? '(Login required)' : ''}</option>
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
                                    <option value="asc">{sortBy === 'name' ? 'A to Z' : 'Nearest First'}</option>
                                    <option value="desc">{sortBy === 'name' ? 'Z to A' : 'Farthest First'}</option>
                                </select>
                            </div>

                            {/* Max Distance */}
                            <div className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                                    <Navigation className="h-3 w-3" /> {t('distance')} ({tc('km')})
                                </label>
                                <input
                                    type="number"
                                    placeholder={userDistrict ? "No limit" : "Login required"}
                                    value={maxDistanceKm ?? ''}
                                    onChange={(e) => setMaxDistanceKm(e.target.value ? Number(e.target.value) : undefined)}
                                    disabled={!userDistrict}
                                    min={0}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                />
                            </div>

                            {/* Facility Filter */}
                            <div className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                                    <Filter className="h-3 w-3" /> {t('facilities')}
                                </label>
                                <select
                                    value={facilityFilter || ''}
                                    onChange={(e) => setFacilityFilter(e.target.value as any || null)}
                                    className="px-3 py-2 bg-muted rounded-lg border-0 outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                                >
                                    <option value="">{tc('all')} {t('facilities')}</option>
                                    <option value="weighbridge">{t('weighbridge')}</option>
                                    <option value="storage">{t('storage')}</option>
                                    <option value="loading_dock">{t('loadingDock')}</option>
                                    <option value="cold_storage">{t('coldStorage')}</option>
                                </select>
                            </div>
                        </div>

                        {/* Clear Filters */}
                        {hasActiveFilters && (
                            <div className="mt-3">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={clearFilters}
                                    className="text-xs"
                                >
                                    {tc('clearAll')}
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
                            <p className="text-muted-foreground">{tc('loading')}</p>
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
                                    {tc('retry')}
                                </Button>
                            </div>
                        </div>
                    )}

                    {/* Empty State */}
                    {!loading && !error && mandis.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="bg-muted rounded-lg p-8 text-center max-w-md">
                                <Search className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
                                <p className="font-medium text-foreground">{t('noResults')}</p>
                                <p className="text-sm text-muted-foreground mt-2">
                                    {searchQuery
                                        ? tc('noResultsFor', { query: searchQuery })
                                        : facilityFilter
                                            ? `No mandis found with ${facilityFilter.replace('_', ' ')} facility. Try a different filter.`
                                            : t('noResults')}
                                </p>
                                {hasActiveFilters && (
                                    <Button
                                        variant="outline"
                                        className="mt-4"
                                        onClick={clearFilters}
                                    >
                                        {tc('clearAll')}
                                    </Button>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Grid View */}
                    {!loading && !error && mandis.length > 0 && viewMode === 'grid' && (
                        <>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
                                {mandis.map((mandi) => (
                                <Card
                                    key={mandi.id}
                                    className="group cursor-pointer hover:shadow-lg hover:border-primary/50 transition-all duration-200 overflow-hidden"
                                    onClick={() => handleMandiClick(mandi)}
                                >
                                    <CardContent className="p-0">
                                        {/* Icon Section */}
                                        <div className="bg-gradient-to-br from-primary/10 to-primary/5 p-6 text-center relative">
                                            <Store className="h-12 w-12 mx-auto text-primary" />
                                            {/* Distance overlay */}
                                            {mandi.distance_km != null && (
                                                <div className="absolute top-2 left-2">
                                                    <Badge variant="secondary" className="text-xs bg-green-100 text-green-800">
                                                        <Navigation className="h-3 w-3 mr-0.5" />
                                                        {mandi.distance_km.toFixed(0)} km
                                                    </Badge>
                                                </div>
                                            )}
                                        </div>

                                        {/* Info Section */}
                                        <div className="p-4">
                                            <h3 className="font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                                                {mandi.name}
                                            </h3>

                                            <div className="mt-2 flex flex-wrap items-center gap-1.5">
                                                <Badge className={`text-xs ${getDistrictColor(mandi.district)}`}>
                                                    <MapPin className="h-3 w-3 mr-0.5" />
                                                    {mandi.district}
                                                </Badge>
                                                <Badge variant="outline" className="text-xs">
                                                    {mandi.state}
                                                </Badge>
                                            </div>

                                            {/* Facilities */}
                                            <div className="mt-2">
                                                <FacilityBadges facilities={mandi.facilities} />
                                            </div>

                                            {/* Top prices */}
                                            {mandi.top_prices && mandi.top_prices.length > 0 && (
                                                <div className="mt-2 pt-2 border-t border-border">
                                                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Top Prices</p>
                                                    {mandi.top_prices.slice(0, 2).map((price, idx) => (
                                                        <div key={idx} className="flex items-center justify-between text-xs">
                                                            <span className="text-muted-foreground truncate mr-2">{price.commodity_name}</span>
                                                            <span className="font-medium text-foreground whitespace-nowrap">
                                                                ₹{price.modal_price.toLocaleString()}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
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
                                        {tc('showMore')} ({mandis.length} / {totalCount})
                                    </Button>
                                </div>
                            )}
                        </>
                    )}

                    {/* List View */}
                    {!loading && !error && mandis.length > 0 && viewMode === 'list' && (
                        <>
                            <div className="space-y-2">
                                {mandis.map((mandi) => (
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
                                                <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                                                    {mandi.name}
                                                </h3>
                                                <div className="flex items-center gap-2 mt-1 flex-wrap">
                                                    <Badge className={`text-xs ${getDistrictColor(mandi.district)}`}>
                                                        <MapPin className="h-3 w-3 mr-0.5" />
                                                        {mandi.district}
                                                    </Badge>
                                                    <span className="text-xs text-muted-foreground">
                                                        {mandi.state}
                                                    </span>
                                                    {mandi.distance_km != null && (
                                                        <span className="text-xs text-green-600 flex items-center gap-0.5">
                                                            <Navigation className="h-3 w-3" />
                                                            {mandi.distance_km.toFixed(1)} km
                                                        </span>
                                                    )}
                                                </div>
                                                {/* Facilities inline */}
                                                <div className="mt-1">
                                                    <FacilityBadges facilities={mandi.facilities} />
                                                </div>
                                            </div>

                                            {/* Top price */}
                                            {mandi.top_prices && mandi.top_prices.length > 0 && (
                                                <div className="hidden md:block text-right shrink-0">
                                                    <p className="text-xs text-muted-foreground">{mandi.top_prices[0].commodity_name}</p>
                                                    <p className="text-sm font-semibold text-foreground">
                                                        ₹{mandi.top_prices[0].modal_price.toLocaleString()}
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
                                        {tc('showMore')} ({mandis.length} / {totalCount})
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
