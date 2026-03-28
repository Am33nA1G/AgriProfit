"use client"

import React, { useState, useEffect } from "react"
import Link from "next/link"
import dynamic from "next/dynamic"
import { useQuery } from "@tanstack/react-query"
import {
  ShoppingCart,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Wheat,
  Store,
  Activity,
  Loader2,
  Package,
  IndianRupee,
  MessageSquare,
  Clock,
  CheckCircle2,
  AlertCircle,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Sidebar } from "@/components/layout/Sidebar"
import { Navbar } from "@/components/layout/Navbar"

// Dynamic import recharts for code splitting - reduces initial bundle size
const PieChart = dynamic(() => import("recharts").then(mod => mod.PieChart), { ssr: false })
const Pie = dynamic(() => import("recharts").then(mod => mod.Pie), { ssr: false })
const ResponsiveContainer = dynamic(() => import("recharts").then(mod => mod.ResponsiveContainer), { ssr: false })
const Cell = dynamic(() => import("recharts").then(mod => mod.Cell), { ssr: false })

import { analyticsService, DashboardData, MarketCoverage } from "@/services/analytics"
import { commoditiesService } from "@/services/commodities"
import type { CommodityWithPrice } from "@/types"
import { notificationsService, Activity as ActivityType } from "@/services/notifications"
import { NotificationBell } from "@/components/layout/NotificationBell"
import { MarketPricesSection } from "@/components/dashboard/MarketPricesSection"

// TypeScript Interfaces
interface StatCard {
  value: string
  label: string
  trend: string
  isHighlighted?: boolean
  icon: React.ReactNode
}

interface Commodity {
  id: string
  name: string
  price: number
  change: number
  mandi: string
  icon: string
}

interface ActivityItem {
  id: string
  type: "price" | "post" | "forecast"
  title: string
  timestamp: string
  detail?: string
}

export default function Dashboard() {
  // Fix hydration: only render time on client
  const [currentTime, setCurrentTime] = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    // Set initial time
    setCurrentTime(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }))
    
    // Update time every minute
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }))
    }, 60000)
    
    return () => clearInterval(timer)
  }, [])

  // Use React Query for automatic refresh and caching
  const { data: dashboardData, isLoading: dashboardLoading, error: dashboardError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => analyticsService.getDashboard(),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })

  const { data: commoditiesData = [] } = useQuery({
    queryKey: ['top-commodities'],
    queryFn: () => commoditiesService.getTopCommodities(5),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })

  const { data: activitiesData = [] } = useQuery({
    queryKey: ['recent-activity'],
    queryFn: () => notificationsService.getRecentActivity(5),
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
  })

  // Transform commodities data
  const commodities: Commodity[] = commoditiesData.map((c: CommodityWithPrice) => ({
    id: c.id,
    name: c.name,
    price: c.current_price || 0,
    change: c.price_change_1d || 0,
    mandi: 'National Avg',
    icon: '🌾'
  }))

  // Transform activities data
  const activities: ActivityItem[] = activitiesData.map((a: ActivityType) => ({
    id: a.id,
    type: a.type,
    title: a.title,
    timestamp: a.timestamp,
    detail: a.detail
  }))

  const loading = dashboardLoading
  const error = dashboardError ? 'Failed to load dashboard data' : null

  // Calculate data freshness and next sync time
  const dataFreshness = dashboardData ? {
    hoursOld: Math.round(dashboardData.market_summary.hours_since_update),
    isStale: dashboardData.market_summary.data_is_stale,
    lastUpdate: new Date(dashboardData.market_summary.last_updated),
    getNextSyncInfo: () => {
      // Sync runs every 6 hours at: 00:00, 06:00, 12:00, 18:00
      const now = new Date()
      const currentHour = now.getHours()
      const syncHours = [0, 6, 12, 18]
      
      // Find next sync hour
      let nextSyncHour = syncHours.find(h => h > currentHour)
      if (!nextSyncHour) {
        nextSyncHour = syncHours[0] // Next day at midnight
      }
      
      const nextSync = new Date(now)
      if (nextSyncHour < currentHour) {
        // Next sync is tomorrow
        nextSync.setDate(nextSync.getDate() + 1)
      }
      nextSync.setHours(nextSyncHour, 0, 0, 0)
      
      const hoursUntilSync = (nextSync.getTime() - now.getTime()) / (1000 * 60 * 60)
      const minutesUntilSync = Math.round((hoursUntilSync % 1) * 60)
      
      return {
        hoursUntilSync: Math.floor(hoursUntilSync),
        minutesUntilSync,
        nextSyncTime: nextSync
      }
    }
  } : null

  // Build stats data from dashboard response
  const statsData: StatCard[] = dashboardData ? [
    {
      value: dashboardData.market_summary.total_commodities.toString(),
      label: "Total Commodities",
      trend: `↗ ${dashboardData.top_commodities.length} tracked`,
      isHighlighted: true,
      icon: <Wheat className="h-5 w-5" />,
    },
    {
      value: dashboardData.market_summary.total_mandis.toString(),
      label: "Active Mandis",
      trend: `↗ ${dashboardData.top_mandis.length} most active`,
      icon: <Store className="h-5 w-5" />,
    },
    {
      value: dashboardData.market_summary.total_price_records.toLocaleString(),
      label: "Price Records",
      trend: dashboardData.market_summary.data_is_stale 
        ? `⚠️ ${Math.round(dashboardData.market_summary.hours_since_update)}h old` 
        : `Updated ${new Date(dashboardData.market_summary.last_updated).toLocaleDateString()}`,
      icon: <Activity className="h-5 w-5" />,
    },
    {
      value: dashboardData.market_summary.total_forecasts.toString(),
      label: "Price Forecasts",
      trend: "Upcoming forecasts",
      icon: <TrendingUp className="h-5 w-5" />,
    },
  ] : [
    { value: "-", label: "Total Commodities", trend: "Loading...", isHighlighted: true, icon: <Wheat className="h-5 w-5" /> },
    { value: "-", label: "Active Mandis", trend: "Loading...", icon: <Store className="h-5 w-5" /> },
    { value: "-", label: "Price Records", trend: "Loading...", icon: <Activity className="h-5 w-5" /> },
    { value: "-", label: "Price Forecasts", trend: "Loading...", icon: <TrendingUp className="h-5 w-5" /> },
  ]

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-black">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 overflow-auto p-4 lg:p-8">
          {/* Page Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Dashboard</h1>
              <p className="text-muted-foreground mt-1">
                Monitor commodity prices across India mandis
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/dashboard/analyze">
                <Button className="bg-green-600 text-white hover:bg-green-700">
                  <BarChart3 className="h-4 w-4 mr-2" />
                  Analyze Inventory
                </Button>
              </Link>
              <Link href="/inventory">
                <Button variant="outline" className="border-primary text-primary hover:bg-primary/10">
                  <Package className="h-4 w-4 mr-2" />
                  My Inventory
                </Button>
              </Link>
              <Link href="/sales">
                <Button variant="outline" className="border-green-600 text-green-600 hover:bg-green-50">
                  <ShoppingCart className="h-4 w-4 mr-2" />
                  Log Sale
                </Button>
              </Link>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-6 lg:mb-8">
            {statsData.map((stat, index) => (
              <Card
                key={stat.label}
                className={`relative overflow-hidden transition-all hover:shadow-md ${stat.isHighlighted
                  ? "bg-primary text-primary-foreground"
                  : "bg-card"
                  }`}
              >
                <CardContent className="p-5 lg:p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div
                      className={`p-2.5 rounded-lg ${stat.isHighlighted
                        ? "bg-primary-foreground/20"
                        : "bg-primary/10"
                        }`}
                    >
                      <div className={stat.isHighlighted ? "text-primary-foreground" : "text-primary"}>
                        {stat.icon}
                      </div>
                    </div>
                  </div>
                  <div>
                    <p
                      className={`text-sm font-medium mb-1 ${stat.isHighlighted
                        ? "text-primary-foreground/80"
                        : "text-muted-foreground"
                        }`}
                    >
                      {stat.label}
                    </p>
                    <p className="text-3xl lg:text-4xl font-bold mb-2">{stat.value}</p>
                    <p
                      className={`text-xs flex items-center gap-1 ${stat.isHighlighted
                        ? "text-primary-foreground/70"
                        : "text-muted-foreground"
                        }`}
                    >
                      {stat.trend.includes("↗") && (
                        <TrendingUp className="h-3 w-3" />
                      )}
                      {stat.trend.replace("↗ ", "")}
                    </p>
                  </div>
                </CardContent>
                {stat.isHighlighted && (
                  <div className="absolute -right-6 -bottom-6 h-24 w-24 rounded-full bg-primary-foreground/10" />
                )}
              </Card>
            ))}
          </div>

          {/* Market Prices Section */}
          <div className="mb-6 lg:mb-8">
            <MarketPricesSection />
          </div>

          {/* Main Grid - Top Commodities & Mandis */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6 mb-6 lg:mb-8">
            {/* Top Commodities */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg font-semibold">Highest Priced Commodities</CardTitle>
                <Link href="/commodities?sortBy=price&sortOrder=desc">
                  <Button variant="ghost" size="sm" className="text-primary">
                    View All
                  </Button>
                </Link>
              </CardHeader>
              <CardContent className="pt-2">
                <div className="space-y-3">
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : commodities.length > 0 ? (
                    commodities.map((commodity) => (
                      <Link
                        key={commodity.id}
                        href={`/commodities/${commodity.id}`}
                        className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors cursor-pointer"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{commodity.icon}</span>
                          <div>
                            <p className="font-medium text-sm">{commodity.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {commodity.mandi}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold text-sm">
                            ₹{commodity.price?.toLocaleString() ?? 'N/A'}
                          </p>
                          <p
                            className={`text-xs flex items-center justify-end gap-1 ${commodity.change >= 0
                              ? "text-primary"
                              : "text-destructive"
                              }`}
                          >
                            {commodity.change >= 0 ? (
                              <TrendingUp className="h-3 w-3" />
                            ) : (
                              <TrendingDown className="h-3 w-3" />
                            )}
                            {commodity.change >= 0 ? "+" : ""}
                            {commodity.change}%
                          </p>
                        </div>
                      </Link>
                    ))
                  ) : (
                    <p className="text-center text-muted-foreground py-4">No commodities found</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Top Mandis */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg font-semibold">Most Active Mandis</CardTitle>
                <Link href="/mandis">
                  <Button variant="ghost" size="sm" className="text-primary">
                    View All
                  </Button>
                </Link>
              </CardHeader>
              <CardContent className="pt-2">
                <div className="space-y-3">
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : dashboardData?.top_mandis?.length ? (
                    dashboardData.top_mandis.slice(0, 5).map((mandi, idx) => (
                      <Link
                        key={mandi.mandi_id}
                        href={`/mandis/${mandi.mandi_id}`}
                        className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors cursor-pointer"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-primary/10 text-primary font-bold text-sm">
                            #{idx + 1}
                          </div>
                          <div>
                            <p className="font-medium text-sm">{mandi.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {mandi.record_count.toLocaleString()} records
                            </p>
                          </div>
                        </div>
                        <Store className="h-4 w-4 text-muted-foreground" />
                      </Link>
                    ))
                  ) : (
                    <p className="text-center text-muted-foreground py-4">No mandis data</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Bottom Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4 lg:gap-6">
            {/* Recent Activity */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold">Recent Activity</CardTitle>
              </CardHeader>
              <CardContent className="pt-2">
                <div className="space-y-3">
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : activities.length > 0 ? (
                    activities.map((activity) => (
                      <div
                        key={activity.id}
                        className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted transition-colors cursor-pointer"
                      >
                        <div
                          className={`p-2 rounded-lg shrink-0 ${activity.type === "price"
                            ? "bg-primary/10 text-primary"
                            : activity.type === "forecast"
                              ? "bg-accent text-foreground"
                              : "bg-muted text-muted-foreground"
                            }`}
                        >
                          {activity.type === "price" && (
                            <IndianRupee className="h-4 w-4" />
                          )}
                          {activity.type === "forecast" && (
                            <TrendingUp className="h-4 w-4" />
                          )}
                          {activity.type === "post" && (
                            <MessageSquare className="h-4 w-4" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate">{activity.title}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {activity.detail}
                          </p>
                        </div>
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {activity.timestamp}
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="text-center text-muted-foreground py-4">
                      No recent activity. Login to see your notifications.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="pt-2">
                <div className="grid grid-cols-2 gap-3">
                  <Link href="/commodities" className="flex flex-col items-center justify-center p-4 rounded-xl bg-muted hover:bg-accent transition-colors text-center group">
                    <div className="p-3 rounded-lg bg-card text-primary mb-3 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                      <Wheat className="h-6 w-6" />
                    </div>
                    <p className="font-medium text-sm">View Commodities</p>
                    <p className="text-xs text-muted-foreground mt-0.5">Browse all products</p>
                  </Link>
                  <Link href="/mandis" className="flex flex-col items-center justify-center p-4 rounded-xl bg-muted hover:bg-accent transition-colors text-center group">
                    <div className="p-3 rounded-lg bg-card text-primary mb-3 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                      <IndianRupee className="h-6 w-6" />
                    </div>
                    <p className="font-medium text-sm">Check Prices</p>
                    <p className="text-xs text-muted-foreground mt-0.5">Latest market prices</p>
                  </Link>
                  <Link href="/mandis" className="flex flex-col items-center justify-center p-4 rounded-xl bg-muted hover:bg-accent transition-colors text-center group">
                    <div className="p-3 rounded-lg bg-card text-primary mb-3 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                      <Store className="h-6 w-6" />
                    </div>
                    <p className="font-medium text-sm">Browse Mandis</p>
                    <p className="text-xs text-muted-foreground mt-0.5">Explore markets</p>
                  </Link>
                  <Link href="/community" className="flex flex-col items-center justify-center p-4 rounded-xl bg-muted hover:bg-accent transition-colors text-center group">
                    <div className="p-3 rounded-lg bg-card text-primary mb-3 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                      <MessageSquare className="h-6 w-6" />
                    </div>
                    <p className="font-medium text-sm">Community Posts</p>
                    <p className="text-xs text-muted-foreground mt-0.5">Join discussions</p>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Data Freshness */}
            <Card className="lg:col-span-2 xl:col-span-1">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold">Data Freshness</CardTitle>
              </CardHeader>
              <CardContent className="pt-2">
                {loading ? (
                  <div className="flex items-center justify-center py-16">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : dataFreshness ? (
                  <div className="flex flex-col items-center justify-center py-6">
                    <div className={`mb-4 ${
                      dataFreshness.isStale ? 'text-amber-500' : 'text-green-600'
                    }`}>
                      {dataFreshness.isStale ? (
                        <AlertCircle className="h-12 w-12" />
                      ) : (
                        <CheckCircle2 className="h-12 w-12" />
                      )}
                    </div>
                    
                    {/* Last Update */}
                    <div className="text-center mb-4">
                      <p className="text-sm text-muted-foreground mb-1">
                        Last price update
                      </p>
                      <p className="text-xl font-bold">
                        {dataFreshness.hoursOld < 1 
                          ? 'Just now' 
                          : `${dataFreshness.hoursOld}h ago`
                        }
                      </p>
                      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium mt-2 ${
                        dataFreshness.isStale 
                          ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                          : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      }`}>
                        {dataFreshness.isStale ? 'Sync Recommended' : 'Up to Date'}
                      </div>
                    </div>
                    
                    {/* Next Sync Countdown */}
                    {(() => {
                      const syncInfo = dataFreshness.getNextSyncInfo()
                      return (
                        <div className="text-center pt-4 border-t w-full">
                          <p className="text-sm text-muted-foreground mb-1">
                            Next auto-sync in
                          </p>
                          <p className="text-lg font-semibold text-primary">
                            {syncInfo.hoursUntilSync}h {syncInfo.minutesUntilSync}m
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            at {syncInfo.nextSyncTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </p>
                        </div>
                      )
                    })()}
                  </div>
                ) : (
                  <p className="text-center text-muted-foreground py-16">No data</p>
                )}
              </CardContent>
            </Card>

            {/* Market Status */}
            <Card className="lg:col-span-2 xl:col-span-3 bg-primary text-primary-foreground overflow-hidden relative">
              <CardContent className="p-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold mb-1">Market Session Active</h3>
                    <p className="text-sm text-primary-foreground/70">
                      Track live prices during trading hours
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-3">
                      <Clock className="h-8 w-8 opacity-70" />
                      <div>
                        <p className="text-sm text-primary-foreground/70">Current Time</p>
                        <p className="text-2xl lg:text-3xl font-mono font-bold">
                          {mounted ? currentTime : '--:--'}
                        </p>
                      </div>
                    </div>
                    <div className="h-12 w-px bg-primary-foreground/20" />
                    <div>
                      <p className="text-sm text-primary-foreground/70">Status</p>
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 bg-green-400 rounded-full animate-pulse" />
                        <span className="font-semibold">Live</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
              <div className="absolute -right-12 -top-12 h-48 w-48 rounded-full bg-primary-foreground/10" />
              <div className="absolute -right-8 top-24 h-24 w-24 rounded-full bg-primary-foreground/5" />
            </Card>
          </div>
        </main>
      </div>
    </div>
  )
}
