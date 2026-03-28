"use client"

import React, { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
    Bell,
    MessageSquare,
    TrendingUp,
    Info,
    Cloud,
    Store,
    Loader2,
    Check,
    Trash2,
    Filter,
    Calendar,
    CheckCheck,
    MoreHorizontal,
    Search,
    X
} from "lucide-react"
import { AppLayout } from "@/components/layout/AppLayout"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator
} from "@/components/ui/dropdown-menu"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import {
    notificationsService,
    Notification,
    NotificationType
} from "@/services/notifications"

// Reuse icons and colors from NotificationBell for consistency
const NotificationIcon: Record<NotificationType, React.ReactNode> = {
    PRICE_ALERT: <TrendingUp className="h-5 w-5 text-green-600 dark:text-green-500" />,
    FORUM_REPLY: <MessageSquare className="h-5 w-5 text-blue-600 dark:text-blue-500" />,
    NEW_POST: <MessageSquare className="h-5 w-5 text-purple-600 dark:text-purple-500" />,
    SYSTEM: <Info className="h-5 w-5 text-gray-600 dark:text-gray-500" />,
    WEATHER_ALERT: <Cloud className="h-5 w-5 text-orange-600 dark:text-orange-500" />,
    MARKET_UPDATE: <Store className="h-5 w-5 text-emerald-600 dark:text-emerald-500" />,
}

const NotificationBg: Record<NotificationType, string> = {
    PRICE_ALERT: "bg-green-100 dark:bg-green-900/30",
    FORUM_REPLY: "bg-blue-100 dark:bg-blue-900/30",
    NEW_POST: "bg-purple-100 dark:bg-purple-900/30",
    SYSTEM: "bg-gray-100 dark:bg-gray-800",
    WEATHER_ALERT: "bg-orange-100 dark:bg-orange-900/30",
    MARKET_UPDATE: "bg-emerald-100 dark:bg-emerald-900/30",
}

// Format date helper
function formatFullTime(dateString: string): string {
    return new Date(dateString).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

export default function NotificationsPage() {
    const router = useRouter()
    const [notifications, setNotifications] = useState<Notification[]>([])
    const [loading, setLoading] = useState(true)
    const [filterType, setFilterType] = useState<string>("ALL")
    const [dateFilter, setDateFilter] = useState<string>("all_time")
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
    const [unreadCount, setUnreadCount] = useState(0)
    const [page, setPage] = useState(1)
    const PAGE_SIZE = 50 // Fetch more to allow client filtering if needed

    const fetchNotifications = useCallback(async () => {
        setLoading(true)
        try {
            // Calculate date params
            let startDate: string | undefined
            const now = new Date()

            if (dateFilter === "today") {
                startDate = new Date(now.setHours(0, 0, 0, 0)).toISOString()
            } else if (dateFilter === "week") {
                const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
                startDate = weekAgo.toISOString()
            } else if (dateFilter === "month") {
                const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
                startDate = monthAgo.toISOString()
            }

            // Map filterType to API type or client filter logic
            // We pass it to backend, but also filter client side for composite types
            let apiType = filterType === "ALL" || filterType === "UNREAD" ? undefined : filterType;
            let unreadOnly = filterType === "UNREAD";

            // Special mapping for tabs
            if (filterType === "PRICE_ALERT") apiType = "PRICE_ALERT"; // Backend might support comma sep?
            // If we are in "Community" tab, we might want FORUM_REPLY and NEW_POST.
            // If backend doesn't support grouping, we fetch ALL and filter.
            // For now, let's fetch ALL and filter client side for complex tabs to be robust.

            // Adjust fetch strategy: Fetch a larger batch
            const response = await notificationsService.getNotifications({
                limit: PAGE_SIZE,
                unread_only: unreadOnly,
                startDate,
                // type: apiType // Skipping strict API type filter for composite tabs, rely on client side
            })

            let items = response.notifications

            // Client-side filtering for Tabs
            if (filterType === "PRICE_ALERT") {
                items = items.filter(n => n.type === "PRICE_ALERT" || n.type === "MARKET_UPDATE")
            } else if (filterType === "COMMUNITY") {
                items = items.filter(n => n.type === "FORUM_REPLY" || n.type === "NEW_POST")
            } else if (filterType === "SYSTEM") {
                items = items.filter(n => n.type === "SYSTEM" || n.type === "WEATHER_ALERT")
            }

            setNotifications(items)
            setUnreadCount(response.unread_count)
        } catch (error) {
            console.error("Failed to fetch notifications", error)
            toast.error("Failed to load notifications")
        } finally {
            setLoading(false)
        }
    }, [filterType, dateFilter])

    useEffect(() => {
        fetchNotifications()
    }, [fetchNotifications])

    // Handlers
    const handleMarkAsRead = async (id: string, e?: React.MouseEvent) => {
        e?.stopPropagation()
        const success = await notificationsService.markAsRead(id)
        if (success) {
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
            setUnreadCount(c => Math.max(0, c - 1))
        }
    }

    const handleDelete = async (id: string, e?: React.MouseEvent) => {
        e?.stopPropagation()
        const success = await notificationsService.deleteNotification(id)
        if (success) {
            setNotifications(prev => prev.filter(n => n.id !== id))
            setSelectedIds(prev => {
                const newSet = new Set(prev)
                newSet.delete(id)
                return newSet
            })
            toast.success("Notification deleted")
        } else {
            toast.error("Failed to delete notification")
        }
    }

    const handleMarkAllRead = async () => {
        const success = await notificationsService.markAllAsRead()
        if (success) {
            setNotifications(prev => prev.map(n => ({ ...n, read: true })))
            setUnreadCount(0)
            toast.success("All notifications marked as read")
        }
    }

    const handleClearAll = async () => {
        if (!confirm("Are you sure you want to clear all notifications?")) return
        const success = await notificationsService.clearAllNotifications()
        if (success) {
            setNotifications([])
            setUnreadCount(0)
            toast.success("All notifications cleared")
        }
    }

    const handleBulkRead = async () => {
        const ids = Array.from(selectedIds)
        const success = await notificationsService.markNotificationsAsRead(ids)
        if (success) {
            setNotifications(prev => prev.map(n => selectedIds.has(n.id) ? { ...n, read: true } : n))
            setSelectedIds(new Set())
            // Ideally re-fetch unread count
            toast.success(`${ids.length} notifications marked as read`)
        }
    }

    const handleBulkDelete = async () => {
        if (!confirm(`Delete ${selectedIds.size} notifications?`)) return
        const ids = Array.from(selectedIds)
        const success = await notificationsService.deleteNotifications(ids)
        if (success) {
            setNotifications(prev => prev.filter(n => !selectedIds.has(n.id)))
            setSelectedIds(new Set())
            toast.success("Notifications deleted")
        }
    }

    const toggleSelection = (id: string, checked: boolean) => {
        setSelectedIds(prev => {
            const newSet = new Set(prev)
            if (checked) newSet.add(id)
            else newSet.delete(id)
            return newSet
        })
    }

    const toggleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedIds(new Set(notifications.map(n => n.id)))
        } else {
            setSelectedIds(new Set())
        }
    }

    const getTabCount = (type: string) => {
        if (type === "ALL") return notifications.length;
        // This count is based on *fetched* items which are already filtered if standard params used
        // But since we fetch ALL and filter client side for tabs, we can count properly?
        // Actually for simplicity, we stick to current view count or ignore badge here
        return 0;
    }

    return (
        <AppLayout>
            <div className="container mx-auto px-4 py-8 max-w-5xl">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Notifications</h1>
                        <p className="text-muted-foreground mt-1">
                            Stay updated with latest alerts and messages
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" onClick={handleMarkAllRead}>
                        <CheckCheck className="h-4 w-4 mr-2" />
                        Mark all read
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleClearAll} className="text-destructive hover:text-destructive">
                        <Trash2 className="h-4 w-4 mr-2" />
                        Clear all
                    </Button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex flex-col gap-6">

                {/* Filters Bar */}
                <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-card p-4 rounded-lg border shadow-sm">
                    <Tabs value={filterType} onValueChange={(v) => {
                        setFilterType(v)
                        setSelectedIds(new Set())
                    }} className="w-full md:w-auto">
                        <TabsList className="grid grid-cols-2 md:grid-cols-5 w-full md:w-auto h-auto md:h-10">
                            <TabsTrigger value="ALL">All</TabsTrigger>
                            <TabsTrigger value="UNREAD">Unread</TabsTrigger>
                            <TabsTrigger value="PRICE_ALERT">Price Alerts</TabsTrigger>
                            <TabsTrigger value="COMMUNITY">Community</TabsTrigger>
                            <TabsTrigger value="SYSTEM">System</TabsTrigger>
                        </TabsList>
                    </Tabs>

                    <div className="flex items-center gap-3 w-full md:w-auto">
                        <Select value={dateFilter} onValueChange={setDateFilter}>
                            <SelectTrigger className="w-[140px]">
                                <Calendar className="h-4 w-4 mr-2 text-muted-foreground" />
                                <SelectValue placeholder="Date" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all_time">All Time</SelectItem>
                                <SelectItem value="today">Today</SelectItem>
                                <SelectItem value="week">This Week</SelectItem>
                                <SelectItem value="month">This Month</SelectItem>
                            </SelectContent>
                        </Select>

                        {selectedIds.size > 0 && (
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="secondary" size="sm" className="ml-auto">
                                        {selectedIds.size} Selected
                                        <MoreHorizontal className="h-4 w-4 ml-2" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                    <DropdownMenuItem onClick={handleBulkRead}>
                                        <Check className="h-4 w-4 mr-2" />
                                        Mark as read
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={handleBulkDelete} className="text-destructive">
                                        <Trash2 className="h-4 w-4 mr-2" />
                                        Delete selected
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        )}
                    </div>
                </div>

                {/* Notifications List */}
                <div className="space-y-4">
                    {/* Header Row */}
                    <div className="flex items-center px-4 py-2 text-sm text-muted-foreground">
                        <Checkbox
                            checked={(notifications?.length ?? 0) > 0 && selectedIds.size === (notifications?.length ?? 0)}
                            onCheckedChange={toggleSelectAll}
                            className="mr-4"
                        />
                        <span>Select All</span>
                        <span className="ml-auto">
                            Showing {notifications?.length ?? 0} notifications
                        </span>
                    </div>

                    {loading ? (
                        <div className="flex flex-col gap-4">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="h-24 w-full bg-muted/20 animate-pulse rounded-lg" />
                            ))}
                        </div>
                    ) : (notifications?.length ?? 0) === 0 ? (
                        <div className="flex flex-col items-center justify-center py-16 text-center border-2 border-dashed rounded-lg">
                            <div className="p-4 rounded-full bg-muted mb-4">
                                <Bell className="h-8 w-8 text-muted-foreground" />
                            </div>
                            <h3 className="text-lg font-semibold">No notifications</h3>
                            <p className="text-muted-foreground max-w-sm mt-1">
                                {filterType === "UNREAD"
                                    ? "You're all caught up! No unread notifications."
                                    : "No notifications found match your current filters."}
                            </p>
                            {filterType !== "ALL" && (
                                <Button variant="link" onClick={() => setFilterType("ALL")} className="mt-4">
                                    View all notifications
                                </Button>
                            )}
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {(notifications ?? []).map((notification) => (
                                <div
                                    key={notification.id}
                                    className={`group relative flex items-start gap-4 p-4 rounded-xl border transition-all hover:shadow-md ${!notification.read ? "bg-card border-l-4 border-l-primary" : "bg-muted/30 border-transparent hover:bg-card"
                                        }`}
                                >
                                    <div className="flex items-center pt-1">
                                        <Checkbox
                                            checked={selectedIds.has(notification.id)}
                                            onCheckedChange={(c) => toggleSelection(notification.id, c as boolean)}
                                        />
                                    </div>

                                    {/* Icon */}
                                    <div className={`flex-shrink-0 p-3 rounded-full ${NotificationBg[notification.type]}`}>
                                        {NotificationIcon[notification.type] || <Bell className="h-5 w-5" />}
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0" onClick={() => notification.link && router.push(notification.link)}>
                                        <div className="flex items-start justify-between gap-2 mb-1">
                                            <div className="flex items-center gap-2">
                                                <h4 className={`text-base font-semibold ${!notification.read ? "text-foreground" : "text-muted-foreground"}`}>
                                                    {notification.title}
                                                </h4>
                                                {!notification.read && (
                                                    <Badge variant="default" className="h-5 px-1.5 text-[10px]">New</Badge>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-muted-foreground whitespace-nowrap">
                                                    {formatFullTime(notification.created_at)}
                                                </span>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                                                    onClick={(e) => handleDelete(notification.id, e)}
                                                >
                                                    <X className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>

                                        <p className="text-sm text-muted-foreground leading-relaxed">
                                            {notification.message}
                                        </p>

                                        {/* Actions */}
                                        <div className="flex items-center gap-3 mt-3">
                                            {!notification.read && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-7 text-xs px-2 -ml-2 text-primary hover:bg-primary/10"
                                                    onClick={(e) => handleMarkAsRead(notification.id, e)}
                                                >
                                                    Mark as read
                                                </Button>
                                            )}
                                            {notification.link && (
                                                <Button
                                                    variant="link"
                                                    size="sm"
                                                    className="h-7 text-xs px-0"
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        router.push(notification.link!)
                                                    }}
                                                >
                                                    View Details
                                                </Button>
                                            )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                    </div>
                </div>
            </div>
        </AppLayout>
    )
}
