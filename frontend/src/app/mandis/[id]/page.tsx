"use client"

import { useParams, useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import {
    ArrowLeft,
    MapPin,
    Phone,
    Mail,
    Globe,
    Clock,
    Navigation,
    Scale,
    Warehouse,
    Truck,
    Snowflake,
    CreditCard,
    Package,
    TrendingUp,
    Loader2
} from "lucide-react"
import { AppLayout } from "@/components/layout/AppLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { mandisService } from "@/services/mandis"
import { authService } from "@/services/auth"
import { useState, useEffect } from "react"

export default function MandiDetailPage() {
    const params = useParams()
    const router = useRouter()
    const mandiId = params.id as string
    const [userDistrict, setUserDistrict] = useState<string | null>(null)
    const [userState, setUserState] = useState<string | null>(null)

    // Get user district and state from auth
    useEffect(() => {
        async function fetchUserDistrict() {
            try {
                const user = await authService.getCurrentUser()
                if (user?.district) {
                    setUserDistrict(user.district)
                    setUserState(user.state || 'Kerala') // Default to Kerala if state not set
                }
            } catch (err) {
                // User not logged in - show mandi without distance
            }
        }
        fetchUserDistrict()
    }, [])

    // Fetch mandi details
    const { data: mandi, isLoading, error } = useQuery({
        queryKey: ['mandi-detail', mandiId, userDistrict, userState],
        queryFn: () => mandisService.getDetails(mandiId, userDistrict, userState),
        enabled: !!mandiId,
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
    })

    if (isLoading) {
        return (
            <AppLayout>
                <div className="min-h-screen bg-background flex items-center justify-center">
                    <div className="text-center">
                        <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
                        <p className="text-muted-foreground">Loading mandi details...</p>
                    </div>
                </div>
            </AppLayout>
        )
    }

    if (error || !mandi) {
        return (
            <AppLayout>
                <div className="min-h-screen bg-background flex items-center justify-center">
                    <div className="text-center max-w-md">
                        <MapPin className="h-12 w-12 text-destructive mx-auto mb-4" />
                        <h2 className="text-xl font-semibold mb-2">Mandi Not Found</h2>
                        <p className="text-muted-foreground mb-4">
                            The mandi you're looking for doesn't exist or has been removed.
                        </p>
                        <Button onClick={() => router.back()}>
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Go Back
                        </Button>
                    </div>
                </div>
            </AppLayout>
        )
    }

    return (
        <AppLayout>
            <div className="min-h-screen bg-background">
                {/* Header */}
                <div className="bg-card border-b border-border">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                        <Button
                            variant="ghost"
                            onClick={() => router.back()}
                            className="mb-4"
                        >
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Mandis
                        </Button>

                        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                                        <MapPin className="h-6 w-6 text-primary" />
                                    </div>
                                    <div>
                                        <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
                                            {mandi.name}
                                        </h1>
                                        {mandi.market_code && (
                                            <p className="text-sm text-muted-foreground">
                                                Code: {mandi.market_code}
                                            </p>
                                        )}
                                    </div>
                                </div>

                                <div className="flex flex-wrap items-center gap-2 mt-3">
                                    <Badge variant="secondary" className="text-sm">
                                        <MapPin className="h-3 w-3 mr-1" />
                                        {mandi.district}, {mandi.state}
                                    </Badge>
                                    {mandi.distance_km != null && (
                                        <Badge variant="outline" className="text-sm text-green-600">
                                            <Navigation className="h-3 w-3 mr-1" />
                                            {mandi.distance_km.toFixed(1)} km away
                                        </Badge>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Left Column - Main Info */}
                        <div className="lg:col-span-2 space-y-6">
                            {/* Contact Information */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Contact Information</CardTitle>
                                    <CardDescription>Get in touch with this mandi</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    {mandi.address && (
                                        <div className="flex items-start gap-3">
                                            <MapPin className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
                                            <div>
                                                <p className="font-medium text-sm">Address</p>
                                                <p className="text-muted-foreground">{mandi.address}</p>
                                                {mandi.pincode && (
                                                    <p className="text-muted-foreground text-sm">PIN: {mandi.pincode}</p>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                    {mandi.contact.phone && (
                                        <div className="flex items-start gap-3">
                                            <Phone className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
                                            <div>
                                                <p className="font-medium text-sm">Phone</p>
                                                <a href={`tel:${mandi.contact.phone}`} className="text-primary hover:underline">
                                                    {mandi.contact.phone}
                                                </a>
                                            </div>
                                        </div>
                                    )}
                                    {mandi.contact.email && (
                                        <div className="flex items-start gap-3">
                                            <Mail className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
                                            <div>
                                                <p className="font-medium text-sm">Email</p>
                                                <a href={`mailto:${mandi.contact.email}`} className="text-primary hover:underline">
                                                    {mandi.contact.email}
                                                </a>
                                            </div>
                                        </div>
                                    )}
                                    {mandi.contact.website && (
                                        <div className="flex items-start gap-3">
                                            <Globe className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
                                            <div>
                                                <p className="font-medium text-sm">Website</p>
                                                <a
                                                    href={mandi.contact.website}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-primary hover:underline"
                                                >
                                                    {mandi.contact.website}
                                                </a>
                                            </div>
                                        </div>
                                    )}
                                    {!mandi.contact.phone && !mandi.contact.email && !mandi.contact.website && !mandi.address && (
                                        <p className="text-muted-foreground text-sm">No contact information available</p>
                                    )}
                                </CardContent>
                            </Card>

                            {/* Operating Hours */}
                            {(mandi.operating_hours.opening_time || mandi.operating_hours.operating_days?.length) && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Operating Hours</CardTitle>
                                        <CardDescription>Market timing and days</CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        {mandi.operating_hours.opening_time && mandi.operating_hours.closing_time && (
                                            <div className="flex items-start gap-3">
                                                <Clock className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
                                                <div>
                                                    <p className="font-medium text-sm">Timing</p>
                                                    <p className="text-muted-foreground">
                                                        {mandi.operating_hours.opening_time} - {mandi.operating_hours.closing_time}
                                                    </p>
                                                </div>
                                            </div>
                                        )}
                                        {mandi.operating_hours.operating_days && mandi.operating_hours.operating_days.length > 0 && (
                                            <div className="flex items-start gap-3">
                                                <Clock className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
                                                <div>
                                                    <p className="font-medium text-sm">Operating Days</p>
                                                    <div className="flex flex-wrap gap-2 mt-2">
                                                        {mandi.operating_hours.operating_days.map((day) => (
                                                            <Badge key={day} variant="secondary" className="text-xs">
                                                                {day}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            )}

                            {/* Current Prices */}
                            {mandi.current_prices && mandi.current_prices.length > 0 && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Current Prices</CardTitle>
                                        <CardDescription>Latest commodity prices at this mandi</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-3">
                                            {mandi.current_prices.slice(0, 10).map((price, index) => (
                                                <div
                                                    key={index}
                                                    className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                                                >
                                                    <div className="flex-1">
                                                        <p className="font-medium">{price.commodity_name}</p>
                                                        <p className="text-xs text-muted-foreground">
                                                            As of {new Date(price.as_of).toLocaleDateString()}
                                                        </p>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="font-bold text-lg text-green-600">
                                                            ₹{price.modal_price.toFixed(2)}
                                                        </p>
                                                        <p className="text-xs text-muted-foreground">per quintal</p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Accepted Commodities */}
                            {mandi.commodities_accepted && mandi.commodities_accepted.length > 0 && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Accepted Commodities</CardTitle>
                                        <CardDescription>Commodities traded at this market</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="flex flex-wrap gap-2">
                                            {mandi.commodities_accepted.map((commodity) => (
                                                <Badge key={commodity} variant="outline" className="text-sm">
                                                    <Package className="h-3 w-3 mr-1" />
                                                    {commodity}
                                                </Badge>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}
                        </div>

                        {/* Right Column - Facilities & Details */}
                        <div className="space-y-6">
                            {/* Facilities */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Facilities</CardTitle>
                                    <CardDescription>Available amenities</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-3">
                                        <div className={`flex items-center gap-3 p-3 rounded-lg ${mandi.facilities.weighbridge ? 'bg-green-50 dark:bg-green-950/20' : 'bg-muted/50'}`}>
                                            <Scale className={`h-5 w-5 ${mandi.facilities.weighbridge ? 'text-green-600' : 'text-muted-foreground'}`} />
                                            <span className={mandi.facilities.weighbridge ? 'font-medium' : 'text-muted-foreground'}>
                                                Weighbridge
                                            </span>
                                            {mandi.facilities.weighbridge && (
                                                <Badge variant="secondary" className="ml-auto text-xs">Available</Badge>
                                            )}
                                        </div>
                                        <div className={`flex items-center gap-3 p-3 rounded-lg ${mandi.facilities.storage ? 'bg-green-50 dark:bg-green-950/20' : 'bg-muted/50'}`}>
                                            <Warehouse className={`h-5 w-5 ${mandi.facilities.storage ? 'text-green-600' : 'text-muted-foreground'}`} />
                                            <span className={mandi.facilities.storage ? 'font-medium' : 'text-muted-foreground'}>
                                                Storage
                                            </span>
                                            {mandi.facilities.storage && (
                                                <Badge variant="secondary" className="ml-auto text-xs">Available</Badge>
                                            )}
                                        </div>
                                        <div className={`flex items-center gap-3 p-3 rounded-lg ${mandi.facilities.loading_dock ? 'bg-green-50 dark:bg-green-950/20' : 'bg-muted/50'}`}>
                                            <Truck className={`h-5 w-5 ${mandi.facilities.loading_dock ? 'text-green-600' : 'text-muted-foreground'}`} />
                                            <span className={mandi.facilities.loading_dock ? 'font-medium' : 'text-muted-foreground'}>
                                                Loading Dock
                                            </span>
                                            {mandi.facilities.loading_dock && (
                                                <Badge variant="secondary" className="ml-auto text-xs">Available</Badge>
                                            )}
                                        </div>
                                        <div className={`flex items-center gap-3 p-3 rounded-lg ${mandi.facilities.cold_storage ? 'bg-green-50 dark:bg-green-950/20' : 'bg-muted/50'}`}>
                                            <Snowflake className={`h-5 w-5 ${mandi.facilities.cold_storage ? 'text-green-600' : 'text-muted-foreground'}`} />
                                            <span className={mandi.facilities.cold_storage ? 'font-medium' : 'text-muted-foreground'}>
                                                Cold Storage
                                            </span>
                                            {mandi.facilities.cold_storage && (
                                                <Badge variant="secondary" className="ml-auto text-xs">Available</Badge>
                                            )}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Payment Methods */}
                            {mandi.payment_methods && mandi.payment_methods.length > 0 && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Payment Methods</CardTitle>
                                        <CardDescription>Accepted payment options</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-2">
                                            {mandi.payment_methods.map((method) => (
                                                <div key={method} className="flex items-center gap-2">
                                                    <CreditCard className="h-4 w-4 text-muted-foreground" />
                                                    <span className="text-sm">{method}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Location Map Placeholder */}
                            {mandi.location.latitude && mandi.location.longitude && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Location</CardTitle>
                                        <CardDescription>Geographic coordinates</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-2 text-sm">
                                            <div className="flex justify-between">
                                                <span className="text-muted-foreground">Latitude:</span>
                                                <span className="font-medium">{mandi.location.latitude.toFixed(6)}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-muted-foreground">Longitude:</span>
                                                <span className="font-medium">{mandi.location.longitude.toFixed(6)}</span>
                                            </div>
                                            <Button
                                                variant="outline"
                                                className="w-full mt-4"
                                                onClick={() => {
                                                    window.open(
                                                        `https://www.google.com/maps/search/?api=1&query=${mandi.location.latitude},${mandi.location.longitude}`,
                                                        '_blank'
                                                    )
                                                }}
                                            >
                                                <Navigation className="h-4 w-4 mr-2" />
                                                Open in Google Maps
                                            </Button>
                                        </div>
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </AppLayout>
    )
}
