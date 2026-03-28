import { Loader2 } from "lucide-react"
import { TableSkeleton, CardSkeleton } from "@/components/ui/table-skeleton"

export default function CommoditiesLoading() {
    return (
        <div className="min-h-screen bg-background p-4 lg:p-8">
            <div className="container mx-auto max-w-7xl">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
                    <div>
                        <div className="h-8 w-40 bg-muted rounded animate-pulse mb-2" />
                        <div className="h-4 w-64 bg-muted rounded animate-pulse" />
                    </div>
                    <div className="flex gap-3">
                        <div className="h-10 w-64 bg-muted rounded-lg animate-pulse" />
                        <div className="h-10 w-32 bg-muted rounded animate-pulse" />
                    </div>
                </div>

                {/* Stats Cards */}
                <CardSkeleton count={4} />

                {/* Table */}
                <div className="mt-8">
                    <TableSkeleton columns={6} rows={8} />
                </div>
            </div>
        </div>
    )
}
