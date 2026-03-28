"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
    Bell,
    MessageSquare,
    TrendingUp,
    AlertCircle,
    Info,
    Cloud,
    Store,
    Loader2,
    Check,
    ChevronRight,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import {
    notificationsService,
    Notification,
    NotificationType,
    formatRelativeTime,
} from "@/services/notifications"

// Icon mapping for notification types
const NotificationIcon: Record<NotificationType, React.ReactNode> = {
    PRICE_ALERT: <TrendingUp className="h-4 w-4 text-green-500" />,
    FORUM_REPLY: <MessageSquare className="h-4 w-4 text-blue-500" />,
    NEW_POST: <MessageSquare className="h-4 w-4 text-purple-500" />,
    SYSTEM: <Info className="h-4 w-4 text-gray-500" />,
    WEATHER_ALERT: <Cloud className="h-4 w-4 text-orange-500" />,
    MARKET_UPDATE: <Store className="h-4 w-4 text-emerald-500" />,
}

// Background color mapping for notification types
const NotificationBg: Record<NotificationType, string> = {
    PRICE_ALERT: "bg-green-50 dark:bg-green-950/30",
    FORUM_REPLY: "bg-blue-50 dark:bg-blue-950/30",
    NEW_POST: "bg-purple-50 dark:bg-purple-950/30",
    SYSTEM: "bg-gray-50 dark:bg-gray-800/50",
    WEATHER_ALERT: "bg-orange-50 dark:bg-orange-950/30",
    MARKET_UPDATE: "bg-emerald-50 dark:bg-emerald-950/30",
}

interface NotificationItemProps {
    notification: Notification
    onRead: (id: string) => void
    onNavigate: (link?: string) => void
}

function NotificationItem({ notification, onRead, onNavigate }: NotificationItemProps) {
    const handleClick = () => {
        if (!notification.read) {
            onRead(notification.id)
        }
        onNavigate(notification.link)
    }

    return (
        <button
            onClick={handleClick}
            className={`w-full text-left p-3 rounded-lg transition-colors hover:bg-muted/50 ${
                !notification.read ? NotificationBg[notification.type] : ""
            }`}
        >
            <div className="flex gap-3">
                {/* Icon */}
                <div className={`flex-shrink-0 mt-0.5 p-2 rounded-full ${
                    notification.read ? "bg-muted" : "bg-background"
                }`}>
                    {NotificationIcon[notification.type] || <Bell className="h-4 w-4" />}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                        <p className={`text-sm font-medium truncate ${
                            notification.read ? "text-muted-foreground" : "text-foreground"
                        }`}>
                            {notification.title}
                        </p>
                        {!notification.read && (
                            <span className="flex-shrink-0 h-2 w-2 mt-1.5 rounded-full bg-primary" />
                        )}
                    </div>
                    <p className={`text-sm mt-0.5 line-clamp-2 ${
                        notification.read ? "text-muted-foreground/70" : "text-muted-foreground"
                    }`}>
                        {notification.message}
                    </p>
                    <p className="text-xs text-muted-foreground/60 mt-1">
                        {formatRelativeTime(notification.created_at)}
                    </p>
                </div>

                {/* Arrow for linked notifications */}
                {notification.link && (
                    <ChevronRight className="flex-shrink-0 h-4 w-4 mt-1 text-muted-foreground/40" />
                )}
            </div>
        </button>
    )
}

interface NotificationBellProps {
    className?: string
    pollInterval?: number // Polling interval in ms (default: 30000)
}

export function NotificationBell({
    className = "",
    pollInterval = 30000,
}: NotificationBellProps) {
    const router = useRouter()
    const [isOpen, setIsOpen] = useState(false)
    const [notifications, setNotifications] = useState<Notification[]>([])
    const [unreadCount, setUnreadCount] = useState(0)
    const [loading, setLoading] = useState(false)
    const [markingAllRead, setMarkingAllRead] = useState(false)
    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

    // Fetch notifications
    const fetchNotifications = useCallback(async () => {
        try {
            setLoading(true)
            const response = await notificationsService.getNotifications({
                limit: 10,
                unread_only: false,
            })
            setNotifications(response.notifications)
            setUnreadCount(response.unread_count)
        } catch (error) {
            console.error("Failed to fetch notifications:", error)
        } finally {
            setLoading(false)
        }
    }, [])

    // Fetch unread count only (lighter call)
    const fetchUnreadCount = useCallback(async () => {
        try {
            const count = await notificationsService.getUnreadCount()
            setUnreadCount(count)
        } catch (error) {
            console.error("Failed to fetch unread count:", error)
        }
    }, [])

    // Initial fetch on mount
    useEffect(() => {
        fetchUnreadCount()
    }, [fetchUnreadCount])

    // Fetch full data when popover opens
    useEffect(() => {
        if (isOpen) {
            fetchNotifications()
        }
    }, [isOpen, fetchNotifications])

    // Polling when popover is open
    useEffect(() => {
        if (isOpen && pollInterval > 0) {
            pollIntervalRef.current = setInterval(() => {
                fetchNotifications()
            }, pollInterval)
        }

        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current)
                pollIntervalRef.current = null
            }
        }
    }, [isOpen, pollInterval, fetchNotifications])

    // Mark single notification as read
    const handleMarkAsRead = async (notificationId: string) => {
        const success = await notificationsService.markAsRead(notificationId)
        if (success) {
            setNotifications(prev =>
                prev.map(n =>
                    n.id === notificationId ? { ...n, read: true } : n
                )
            )
            setUnreadCount(prev => Math.max(0, prev - 1))
        }
    }

    // Mark all as read
    const handleMarkAllAsRead = async () => {
        setMarkingAllRead(true)
        const success = await notificationsService.markAllAsRead()
        if (success) {
            setNotifications(prev => prev.map(n => ({ ...n, read: true })))
            setUnreadCount(0)
        }
        setMarkingAllRead(false)
    }

    // Navigate to linked page
    const handleNavigate = (link?: string) => {
        if (link) {
            setIsOpen(false)
            router.push(link)
        }
    }

    return (
        <Popover open={isOpen} onOpenChange={setIsOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="ghost"
                    size="icon"
                    className={`relative ${className}`}
                    aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
                >
                    <Bell className="h-5 w-5 text-muted-foreground" />
                    {unreadCount > 0 && (
                        <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-destructive rounded-full">
                            {unreadCount > 99 ? "99+" : unreadCount}
                        </span>
                    )}
                </Button>
            </PopoverTrigger>

            <PopoverContent
                align="end"
                sideOffset={8}
                className="w-[380px] p-0 shadow-lg"
            >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                    <h3 className="font-semibold text-foreground">Notifications</h3>
                    {unreadCount > 0 && (
                        <button
                            onClick={handleMarkAllAsRead}
                            disabled={markingAllRead}
                            className="text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50 flex items-center gap-1"
                        >
                            {markingAllRead ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                                <Check className="h-3 w-3" />
                            )}
                            Mark all as read
                        </button>
                    )}
                </div>

                {/* Notification List */}
                <div className="max-h-[400px] overflow-y-auto">
                    {loading && notifications.length === 0 ? (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                    ) : notifications.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
                            <div className="p-3 rounded-full bg-muted mb-3">
                                <Bell className="h-6 w-6 text-muted-foreground" />
                            </div>
                            <p className="font-medium text-foreground">No notifications yet</p>
                            <p className="text-sm text-muted-foreground mt-1">
                                We'll notify you when something important happens
                            </p>
                        </div>
                    ) : (
                        <div className="p-2 space-y-1">
                            {notifications.map(notification => (
                                <NotificationItem
                                    key={notification.id}
                                    notification={notification}
                                    onRead={handleMarkAsRead}
                                    onNavigate={handleNavigate}
                                />
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                {notifications.length > 0 && (
                    <div className="border-t border-border p-2">
                        <Link
                            href="/notifications"
                            onClick={() => setIsOpen(false)}
                            className="flex items-center justify-center gap-2 w-full py-2 text-sm font-medium text-primary hover:bg-muted rounded-lg transition-colors"
                        >
                            View all notifications
                            <ChevronRight className="h-4 w-4" />
                        </Link>
                    </div>
                )}
            </PopoverContent>
        </Popover>
    )
}

export default NotificationBell
