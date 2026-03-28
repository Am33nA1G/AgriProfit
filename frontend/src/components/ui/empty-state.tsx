"use client"

import React, { ReactNode } from "react"
import {
    Package,
    FileText,
    Users,
    Bell,
    ShoppingCart,
    MapPin,
    MessageSquare,
    TrendingUp,
    Search,
    Inbox,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

type EmptyStateVariant =
    | "generic"
    | "posts"
    | "users"
    | "notifications"
    | "commodities"
    | "mandis"
    | "inventory"
    | "sales"
    | "search"

interface EmptyStateProps {
    variant?: EmptyStateVariant
    title?: string
    description?: string
    icon?: ReactNode
    action?: {
        label: string
        onClick: () => void
    }
    className?: string
}

const defaultContent: Record<EmptyStateVariant, { icon: ReactNode; title: string; description: string }> = {
    generic: {
        icon: <Inbox className="h-12 w-12" />,
        title: "No items found",
        description: "There are no items to display at the moment.",
    },
    posts: {
        icon: <MessageSquare className="h-12 w-12" />,
        title: "No posts yet",
        description: "Be the first to start a conversation in the community!",
    },
    users: {
        icon: <Users className="h-12 w-12" />,
        title: "No users found",
        description: "There are no users matching your criteria.",
    },
    notifications: {
        icon: <Bell className="h-12 w-12" />,
        title: "No notifications",
        description: "You're all caught up! No new notifications.",
    },
    commodities: {
        icon: <ShoppingCart className="h-12 w-12" />,
        title: "No commodities found",
        description: "No commodities are available at the moment.",
    },
    mandis: {
        icon: <MapPin className="h-12 w-12" />,
        title: "No mandis found",
        description: "No mandis match your search criteria.",
    },
    inventory: {
        icon: <Package className="h-12 w-12" />,
        title: "No inventory items",
        description: "Start by adding items to your inventory.",
    },
    sales: {
        icon: <TrendingUp className="h-12 w-12" />,
        title: "No sales history",
        description: "Your sales records will appear here.",
    },
    search: {
        icon: <Search className="h-12 w-12" />,
        title: "No results found",
        description: "Try adjusting your search or filter criteria.",
    },
}

export function EmptyState({
    variant = "generic",
    title,
    description,
    icon,
    action,
    className = "",
}: EmptyStateProps) {
    const content = defaultContent[variant]

    return (
        <Card className={`p-12 text-center ${className}`}>
            <div className="flex flex-col items-center">
                <div className="p-4 rounded-full bg-muted mb-4 text-muted-foreground">
                    {icon || content.icon}
                </div>
                <h3 className="text-lg font-semibold mb-2">
                    {title || content.title}
                </h3>
                <p className="text-muted-foreground max-w-sm mb-4">
                    {description || content.description}
                </p>
                {action && (
                    <Button onClick={action.onClick}>
                        {action.label}
                    </Button>
                )}
            </div>
        </Card>
    )
}

// Inline empty state for smaller areas
export function InlineEmptyState({
    message = "No items found",
    className = "",
}: {
    message?: string
    className?: string
}) {
    return (
        <div className={`flex items-center justify-center py-8 text-muted-foreground ${className}`}>
            <Inbox className="h-5 w-5 mr-2" />
            <span>{message}</span>
        </div>
    )
}

export default EmptyState
