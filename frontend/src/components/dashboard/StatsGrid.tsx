import { Card } from "@/components/ui/card"
import { ArrowUpRight, TrendingUp, TrendingDown } from "lucide-react"
import { cn } from "@/lib/utils"

interface StatsCardProps {
  value: string
  label: string
  trend: string
  isHighlighted?: boolean
  className?: string
}

export function StatsCard({ 
  value, 
  label, 
  trend, 
  isHighlighted = false,
  className 
}: StatsCardProps) {
  const isPositive = !trend.startsWith("-")
  
  return (
    <Card
      className={cn(
        "relative overflow-hidden rounded-2xl border p-5 transition-shadow hover:shadow-md",
        isHighlighted 
          ? "border-0 bg-[#166534] text-white shadow-lg" 
          : "border-stone-200 bg-white text-stone-900 shadow-sm",
        className
      )}
    >
      {/* Header with label and arrow button */}
      <div className="flex items-start justify-between">
        <span className={cn(
          "text-sm font-medium",
          isHighlighted ? "text-emerald-100" : "text-stone-600"
        )}>
          {label}
        </span>
        <button 
          type="button"
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full border transition-colors",
            isHighlighted 
              ? "border-white/30 bg-white/10 hover:bg-white/20" 
              : "border-stone-200 bg-white hover:bg-stone-50"
          )}
        >
          <ArrowUpRight className={cn(
            "h-4 w-4",
            isHighlighted ? "text-white" : "text-stone-700"
          )} />
        </button>
      </div>
      
      {/* Main value */}
      <div className="mt-4">
        <span className={cn(
          "text-5xl font-bold tracking-tight",
          isHighlighted ? "text-white" : "text-stone-900"
        )}>
          {value}
        </span>
      </div>
      
      {/* Trend indicator */}
      <div className="mt-4 flex items-center gap-1.5">
        <div className={cn(
          "flex items-center gap-1 text-xs font-medium",
          isHighlighted 
            ? isPositive ? "text-emerald-200" : "text-red-300"
            : isPositive ? "text-emerald-600" : "text-red-500"
        )}>
          {isPositive ? (
            <TrendingUp className="h-3.5 w-3.5" />
          ) : (
            <TrendingDown className="h-3.5 w-3.5" />
          )}
          <span>{trend}</span>
        </div>
        <span className={cn(
          "text-xs",
          isHighlighted ? "text-emerald-200/80" : "text-stone-500"
        )}>
          from last month
        </span>
      </div>
    </Card>
  )
}
