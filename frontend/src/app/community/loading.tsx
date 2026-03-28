import { Loader2 } from "lucide-react"
import { ListSkeleton } from "@/components/ui/table-skeleton"

export default function CommunityLoading() {
    return (
        <div className="min-h-screen bg-background">
            <div className="container mx-auto px-4 py-8 max-w-4xl">
                {/* Header Skeleton */}
                <div className="mb-8">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                            <div className="h-9 w-64 bg-muted rounded animate-pulse mb-2" />
                            <div className="h-4 w-96 bg-muted rounded animate-pulse" />
                        </div>
                        <div className="h-10 w-32 bg-muted rounded animate-pulse" />
                    </div>
                </div>

                {/* Filter Tabs Skeleton */}
                <div className="mb-6 space-y-4">
                    <div className="flex flex-wrap gap-2">
                        {[1, 2, 3, 4, 5].map((i) => (
                            <div key={i} className="h-8 w-20 bg-muted rounded-md animate-pulse" />
                        ))}
                    </div>
                    <div className="flex gap-3">
                        <div className="flex-1 h-10 bg-muted rounded-lg animate-pulse" />
                        <div className="h-10 w-48 bg-muted rounded-lg animate-pulse" />
                    </div>
                </div>

                {/* Posts List Skeleton */}
                <ListSkeleton count={5} />
            </div>
        </div>
    )
}
