export default function ForecastLoading() {
    return (
        <div className="min-h-screen bg-background p-4 lg:p-8">
            <div className="container mx-auto max-w-5xl">
                {/* Header */}
                <div className="mb-8">
                    <div className="h-8 w-64 bg-muted rounded animate-pulse mb-2" />
                    <div className="h-4 w-96 bg-muted rounded animate-pulse" />
                </div>

                {/* Selectors */}
                <div className="flex flex-wrap gap-3 mb-8">
                    <div className="h-10 w-48 bg-muted rounded-lg animate-pulse" />
                    <div className="h-10 w-48 bg-muted rounded-lg animate-pulse" />
                    <div className="h-10 w-48 bg-muted rounded-lg animate-pulse" />
                    <div className="h-10 w-32 bg-muted rounded-lg animate-pulse" />
                </div>

                {/* Chart placeholder */}
                <div className="h-80 bg-muted/30 rounded-xl border border-border/50 animate-pulse mb-8" />

                {/* Badges */}
                <div className="flex gap-3 mb-6">
                    <div className="h-8 w-24 bg-muted rounded-full animate-pulse" />
                    <div className="h-8 w-32 bg-muted rounded-full animate-pulse" />
                    <div className="h-8 w-28 bg-muted rounded-full animate-pulse" />
                </div>

                {/* Price range */}
                <div className="h-20 w-full bg-muted rounded-xl animate-pulse" />
            </div>
        </div>
    )
}
