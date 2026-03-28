import { Loader2 } from "lucide-react"
import { CardSkeleton } from "@/components/ui/table-skeleton"

export default function DashboardLoading() {
    return (
        <div className="flex min-h-screen bg-background">
            {/* Sidebar Skeleton */}
            <aside className="hidden lg:block w-64 bg-card border-r border-border p-6">
                <div className="flex items-center gap-3 mb-8">
                    <div className="h-10 w-10 rounded-xl bg-muted animate-pulse" />
                    <div className="h-6 w-24 bg-muted rounded animate-pulse" />
                </div>
                <div className="space-y-2">
                    {[1, 2, 3, 4, 5].map((i) => (
                        <div key={i} className="h-10 bg-muted rounded-lg animate-pulse" />
                    ))}
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 p-4 lg:p-8">
                {/* Header Skeleton */}
                <div className="flex items-center justify-between mb-8">
                    <div className="space-y-2">
                        <div className="h-8 w-32 bg-muted rounded animate-pulse" />
                        <div className="h-4 w-48 bg-muted rounded animate-pulse" />
                    </div>
                    <div className="flex gap-3">
                        <div className="h-10 w-32 bg-muted rounded animate-pulse" />
                        <div className="h-10 w-24 bg-muted rounded animate-pulse" />
                    </div>
                </div>

                {/* Stats Grid Skeleton */}
                <CardSkeleton count={4} />

                {/* Loading indicator */}
                <div className="flex items-center justify-center py-12 mt-8">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
            </main>
        </div>
    )
}
