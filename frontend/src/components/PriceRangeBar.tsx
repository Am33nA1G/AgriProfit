interface PriceRangeBarProps {
    price_low: number | null
    price_mid: number | null
    price_high: number | null
}

export default function PriceRangeBar({ price_low, price_mid, price_high }: PriceRangeBarProps) {
    if (price_mid == null) return null

    const hasRange = price_low != null && price_high != null

    return (
        <div className="p-5 rounded-xl bg-card border border-border/50 shadow-sm">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-4">
                Predicted Price Range
            </h3>

            {hasRange ? (
                <div>
                    {/* Labels */}
                    <div className="flex justify-between text-xs text-muted-foreground mb-2">
                        <span>Low</span>
                        <span>Mid</span>
                        <span>High</span>
                    </div>
                    {/* Track */}
                    <div className="relative h-6 flex items-center mb-2">
                        <div className="absolute left-0 right-0 h-0.5 bg-border/60 rounded-full" />
                        {/* Low dot */}
                        <div className="absolute left-0 h-3 w-3 rounded-full bg-muted-foreground/50 border-2 border-background -translate-x-1/2" />
                        {/* Mid dot (larger) */}
                        <div className="absolute left-1/2 h-4 w-4 rounded-full bg-foreground border-2 border-background -translate-x-1/2" />
                        {/* High dot */}
                        <div className="absolute right-0 h-3 w-3 rounded-full bg-muted-foreground/50 border-2 border-background translate-x-1/2" />
                    </div>
                    {/* Prices */}
                    <div className="flex justify-between items-baseline">
                        <p className="text-base font-semibold text-muted-foreground">
                            ₹{price_low!.toFixed(2)}
                        </p>
                        <p className="text-2xl font-bold">
                            ₹{price_mid.toFixed(2)}
                        </p>
                        <p className="text-base font-semibold text-muted-foreground">
                            ₹{price_high!.toFixed(2)}
                        </p>
                    </div>
                </div>
            ) : (
                <div className="text-center">
                    <p className="text-xs text-muted-foreground mb-1">Mid</p>
                    <p className="text-2xl font-bold">₹{price_mid.toFixed(2)}</p>
                </div>
            )}
        </div>
    )
}
