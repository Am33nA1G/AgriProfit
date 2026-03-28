import { TableSkeleton, CardSkeleton } from "@/components/ui/table-skeleton"

export default function TransportLoading() {
    return (
        <div className="min-h-screen bg-background p-4 lg:p-8">
            <div className="container mx-auto max-w-7xl">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
                    <div>
                        <div className="h-8 w-48 bg-muted rounded animate-pulse mb-2" />
                        <div className="h-4 w-72 bg-muted rounded animate-pulse" />
                    </div>
                    <div className="h-10 w-40 bg-muted rounded animate-pulse" />
                </div>

                {/* Stats Cards */}
                <CardSkeleton count={4} />

                {/* Filters */}
                <div className="flex flex-wrap gap-3 mt-8 mb-6">
                    <div className="h-10 w-48 bg-muted rounded-lg animate-pulse" />
                    <div className="h-10 w-32 bg-muted rounded animate-pulse" />
                    <div className="h-10 w-36 bg-muted rounded animate-pulse" />
                </div>

                {/* Table */}
                <TableSkeleton columns={7} rows={8} />
            </div>
        </div>
    )
}
