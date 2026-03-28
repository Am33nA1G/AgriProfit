import { ListSkeleton } from "@/components/ui/table-skeleton"

export default function NotificationsLoading() {
    return (
        <div className="container mx-auto px-4 py-8 max-w-5xl">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <div className="h-9 w-40 bg-muted rounded animate-pulse mb-2" />
                    <div className="h-4 w-64 bg-muted rounded animate-pulse" />
                </div>
                <div className="flex items-center gap-2">
                    <div className="h-9 w-32 bg-muted rounded animate-pulse" />
                    <div className="h-9 w-24 bg-muted rounded animate-pulse" />
                </div>
            </div>

            {/* Filters Bar */}
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-card p-4 rounded-lg border mb-6">
                <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((i) => (
                        <div key={i} className="h-9 w-24 bg-muted rounded animate-pulse" />
                    ))}
                </div>
                <div className="h-9 w-36 bg-muted rounded animate-pulse" />
            </div>

            {/* Notifications List */}
            <ListSkeleton count={8} />
        </div>
    )
}
