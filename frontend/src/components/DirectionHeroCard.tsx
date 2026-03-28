import { TrendingUp, TrendingDown, ArrowRight, Lock } from "lucide-react"

interface DirectionHeroCardProps {
    direction: 'up' | 'down' | 'flat' | 'uncertain'
    confidence_colour: 'Green' | 'Yellow' | 'Red'
    horizon_days: number
    mape_pct: number | null
    model_version: string | null
    r2_score: number | null
}

const CONFIDENCE_STYLES: Record<string, { card: string; text: string; divider: string }> = {
    Green: {
        card: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-800",
        text: "text-emerald-700 dark:text-emerald-300",
        divider: "border-emerald-200 dark:border-emerald-800",
    },
    Yellow: {
        card: "bg-amber-50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-800",
        text: "text-amber-700 dark:text-amber-300",
        divider: "border-amber-200 dark:border-amber-800",
    },
    Red: {
        card: "bg-red-50 border-red-200 dark:bg-red-950/20 dark:border-red-800",
        text: "text-red-700 dark:text-red-300",
        divider: "border-red-200 dark:border-red-800",
    },
}

const CONFIDENCE_LABELS: Record<string, string> = {
    Green: "Reliable",
    Yellow: "Directional only",
    Red: "Low Confidence",
}

const MODEL_LABELS: Record<string, string> = {
    v5: "v5 · LightGBM",
    legacy: "Legacy · Prophet",
    seasonal: "Seasonal Avg",
}

function getDirectionContent(
    direction: DirectionHeroCardProps['direction'],
    confidence_colour: DirectionHeroCardProps['confidence_colour'],
    horizon_days: number
): { icon: React.ElementType; label: string; subtext: string } {
    if (confidence_colour === 'Red' || direction === 'uncertain') {
        return {
            icon: Lock,
            label: 'UNCERTAIN',
            subtext: 'Do not use for financial decisions',
        }
    }
    if (direction === 'up') {
        return {
            icon: TrendingUp,
            label: 'RISING',
            subtext: `Prices expected to rise over the next ${horizon_days} days`,
        }
    }
    if (direction === 'down') {
        return {
            icon: TrendingDown,
            label: 'FALLING',
            subtext: `Prices expected to fall over the next ${horizon_days} days`,
        }
    }
    return {
        icon: ArrowRight,
        label: 'STABLE',
        subtext: `Prices holding steady over the next ${horizon_days} days`,
    }
}

export default function DirectionHeroCard({
    direction,
    confidence_colour,
    horizon_days,
    mape_pct,
    model_version,
    r2_score,
}: DirectionHeroCardProps) {
    const styles = CONFIDENCE_STYLES[confidence_colour]
    const { icon: Icon, label, subtext } = getDirectionContent(direction, confidence_colour, horizon_days)

    return (
        <div className={`p-6 rounded-xl border-2 ${styles.card}`}>
            <div className="flex items-start gap-4">
                <Icon className={`h-12 w-12 flex-shrink-0 mt-1 ${styles.text}`} />
                <div className="flex-1 min-w-0">
                    <p className={`text-4xl font-black tracking-tight ${styles.text}`}>
                        {label}
                    </p>
                    <p className={`text-sm mt-1 ${styles.text} opacity-80`}>
                        {subtext}
                    </p>
                </div>
            </div>

            {/* Technical details — visible but receded */}
            <div className={`flex flex-wrap items-center gap-3 mt-4 pt-3 border-t ${styles.divider}`}>
                <span className={`text-xs font-medium ${styles.text} opacity-70`}>
                    {CONFIDENCE_LABELS[confidence_colour]}
                    {mape_pct != null && (
                        <span className="font-mono"> ±{mape_pct.toFixed(0)}%</span>
                    )}
                </span>
                {model_version && MODEL_LABELS[model_version] && (
                    <span className={`text-xs ${styles.text} opacity-60`}>
                        {MODEL_LABELS[model_version]}
                    </span>
                )}
                {r2_score != null && r2_score > 0 && (
                    <span className={`text-xs font-mono ${styles.text} opacity-60`}>
                        R² {r2_score.toFixed(2)}
                    </span>
                )}
            </div>
        </div>
    )
}
