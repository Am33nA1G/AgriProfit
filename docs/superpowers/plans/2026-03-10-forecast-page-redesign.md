# Forecast Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the forecast page's badge row and price card with a Direction Hero Card and Price Range Bar so farmers can answer "is it going up or down?" at a glance.

**Architecture:** Two new focused React components (`DirectionHeroCard`, `PriceRangeBar`) extract the visual logic out of `page.tsx`. The page becomes a thin orchestrator that passes forecast data to these components. No backend changes — frontend only.

**Tech Stack:** Next.js, React, TypeScript, Tailwind CSS, Vitest + @testing-library/react (jsdom), lucide-react

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/components/DirectionHeroCard.tsx` | Hero card: direction label, icon, confidence color, technical badges |
| Create | `frontend/src/components/PriceRangeBar.tsx` | Visual price range track with Low/Mid/High |
| Create | `frontend/src/components/__tests__/DirectionHeroCard.test.tsx` | Unit tests for hero card |
| Create | `frontend/src/components/__tests__/PriceRangeBar.test.tsx` | Unit tests for price range bar |
| Modify | `frontend/src/app/forecast/page.tsx` | Wire new components, remove replaced sections |

---

## Chunk 1: DirectionHeroCard

### Task 1: DirectionHeroCard — test + implement

**Files:**
- Create: `frontend/src/components/DirectionHeroCard.tsx`
- Create: `frontend/src/components/__tests__/DirectionHeroCard.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/__tests__/DirectionHeroCard.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

vi.mock('lucide-react', () => {
    const S = ({ className }: { className?: string }) => <svg className={className} />
    return { TrendingUp: S, TrendingDown: S, ArrowRight: S, Lock: S }
})

import DirectionHeroCard from '../DirectionHeroCard'

describe('DirectionHeroCard', () => {
    it('shows RISING for up direction', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={12}
                model_version="v5"
                r2_score={0.84}
            />
        )
        expect(screen.getByText('RISING')).toBeInTheDocument()
        expect(screen.getByText(/Prices expected to rise/)).toBeInTheDocument()
    })

    it('shows FALLING for down direction', () => {
        render(
            <DirectionHeroCard
                direction="down"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={null}
                model_version={null}
                r2_score={null}
            />
        )
        expect(screen.getByText('FALLING')).toBeInTheDocument()
        expect(screen.getByText(/Prices expected to fall/)).toBeInTheDocument()
    })

    it('shows STABLE for flat direction', () => {
        render(
            <DirectionHeroCard
                direction="flat"
                confidence_colour="Yellow"
                horizon_days={7}
                mape_pct={28}
                model_version="legacy"
                r2_score={null}
            />
        )
        expect(screen.getByText('STABLE')).toBeInTheDocument()
        expect(screen.getByText(/Prices holding steady/)).toBeInTheDocument()
    })

    it('shows UNCERTAIN and warning for Red confidence regardless of direction', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Red"
                horizon_days={7}
                mape_pct={55}
                model_version="legacy"
                r2_score={null}
            />
        )
        expect(screen.getByText('UNCERTAIN')).toBeInTheDocument()
        expect(screen.getByText(/Do not use for financial decisions/)).toBeInTheDocument()
    })

    it('shows UNCERTAIN for uncertain direction', () => {
        render(
            <DirectionHeroCard
                direction="uncertain"
                confidence_colour="Yellow"
                horizon_days={7}
                mape_pct={null}
                model_version={null}
                r2_score={null}
            />
        )
        expect(screen.getByText('UNCERTAIN')).toBeInTheDocument()
    })

    it('shows mape_pct when provided', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={12}
                model_version={null}
                r2_score={null}
            />
        )
        expect(screen.getByText(/±12%/)).toBeInTheDocument()
    })

    it('shows R² when positive', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={null}
                model_version="v5"
                r2_score={0.84}
            />
        )
        expect(screen.getByText(/R² 0.84/)).toBeInTheDocument()
    })

    it('does not show R² when negative', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={null}
                model_version="v5"
                r2_score={-0.1}
            />
        )
        expect(screen.queryByText(/R²/)).not.toBeInTheDocument()
    })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run src/components/__tests__/DirectionHeroCard.test.tsx
```
Expected: FAIL with "Cannot find module '../DirectionHeroCard'"

- [ ] **Step 3: Implement DirectionHeroCard**

Create `frontend/src/components/DirectionHeroCard.tsx`:

```tsx
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run src/components/__tests__/DirectionHeroCard.test.tsx
```
Expected: 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DirectionHeroCard.tsx frontend/src/components/__tests__/DirectionHeroCard.test.tsx
git commit -m "feat(forecast): add DirectionHeroCard component"
```

---

## Chunk 2: PriceRangeBar

### Task 2: PriceRangeBar — test + implement

**Files:**
- Create: `frontend/src/components/PriceRangeBar.tsx`
- Create: `frontend/src/components/__tests__/PriceRangeBar.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/__tests__/PriceRangeBar.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import PriceRangeBar from '../PriceRangeBar'

describe('PriceRangeBar', () => {
    it('renders low, mid, and high prices', () => {
        render(<PriceRangeBar price_low={420} price_mid={510} price_high={590} />)
        expect(screen.getByText('₹420.00')).toBeInTheDocument()
        expect(screen.getByText('₹510.00')).toBeInTheDocument()
        expect(screen.getByText('₹590.00')).toBeInTheDocument()
    })

    it('shows Low, Mid, High labels when all values present', () => {
        render(<PriceRangeBar price_low={420} price_mid={510} price_high={590} />)
        expect(screen.getByText('Low')).toBeInTheDocument()
        expect(screen.getByText('Mid')).toBeInTheDocument()
        expect(screen.getByText('High')).toBeInTheDocument()
    })

    it('renders only mid when low and high are null', () => {
        render(<PriceRangeBar price_low={null} price_mid={510} price_high={null} />)
        expect(screen.getByText('₹510.00')).toBeInTheDocument()
        expect(screen.queryByText('Low')).not.toBeInTheDocument()
        expect(screen.queryByText('High')).not.toBeInTheDocument()
    })

    it('renders nothing when mid is null', () => {
        const { container } = render(
            <PriceRangeBar price_low={null} price_mid={null} price_high={null} />
        )
        expect(container.firstChild).toBeNull()
    })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run src/components/__tests__/PriceRangeBar.test.tsx
```
Expected: FAIL with "Cannot find module '../PriceRangeBar'"

- [ ] **Step 3: Implement PriceRangeBar**

Create `frontend/src/components/PriceRangeBar.tsx`:

```tsx
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run src/components/__tests__/PriceRangeBar.test.tsx
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PriceRangeBar.tsx frontend/src/components/__tests__/PriceRangeBar.test.tsx
git commit -m "feat(forecast): add PriceRangeBar component"
```

---

## Chunk 3: Wire into forecast/page.tsx

### Task 3: Update forecast/page.tsx

**Files:**
- Modify: `frontend/src/app/forecast/page.tsx`
- Modify: `frontend/src/app/forecast/__tests__/page.test.tsx`

**Context — what stays vs what changes:**
- `CONFIDENCE_CONFIG` + `confConfig` variable → **KEEP** (still used by red-confidence warning banner, lines ~289–305)
- `isV5` variable → **KEEP** (still used by horizon dropdown)
- `DIRECTION_CONFIG` + `dirConfig` variable → **REMOVE** (only used in badges row being replaced)
- `MODEL_VERSION_CONFIG` → **REMOVE** (moved into DirectionHeroCard)

- [ ] **Step 1: Add new imports**

In `frontend/src/app/forecast/page.tsx`, add after the existing imports block:

```tsx
import DirectionHeroCard from "@/components/DirectionHeroCard"
import PriceRangeBar from "@/components/PriceRangeBar"
```

- [ ] **Step 2: Remove DIRECTION_CONFIG constant**

Delete the entire `DIRECTION_CONFIG` object (lines 40–61):

```tsx
// DELETE THIS ENTIRE BLOCK:
const DIRECTION_CONFIG = {
    up: { ... },
    down: { ... },
    flat: { ... },
    uncertain: { ... },
}
```

- [ ] **Step 3: Remove MODEL_VERSION_CONFIG constant**

Delete the entire `MODEL_VERSION_CONFIG` object (lines 81–94):

```tsx
// DELETE THIS ENTIRE BLOCK:
const MODEL_VERSION_CONFIG: Record<string, { label: string; className: string }> = {
    v5: { ... },
    legacy: { ... },
    seasonal: { ... },
}
```

- [ ] **Step 4: Remove dirConfig variable**

Delete this line (~line 134):

```tsx
// DELETE:
const dirConfig = forecast ? DIRECTION_CONFIG[forecast.direction] : null
```

- [ ] **Step 5: Replace the badges row with DirectionHeroCard**

Find `{/* Badges row */}` block (the entire section from `<div className="flex flex-wrap items-center gap-3"` to its closing `</div>`) and replace with:

```tsx
{/* Direction Hero Card */}
<DirectionHeroCard
    direction={forecast.direction}
    confidence_colour={forecast.confidence_colour}
    horizon_days={forecast.horizon_days}
    mape_pct={forecast.mape_pct}
    model_version={forecast.model_version ?? null}
    r2_score={forecast.r2_score}
/>
```

- [ ] **Step 6: Replace the Price Range Card with PriceRangeBar**

Find `{/* Price Range Card */}` block (the entire `forecast.price_mid && (...)` section) and replace with:

```tsx
{/* Price Range */}
<PriceRangeBar
    price_low={forecast.price_low}
    price_mid={forecast.price_mid}
    price_high={forecast.price_high}
/>
```

- [ ] **Step 7: Update the chart section**

Find the chart `<div>` wrapper:

```tsx
// OLD:
<div className="p-5 rounded-xl bg-card border border-border/50 shadow-sm">
    <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-4">
        Forecast Chart
    </h3>
    <ForecastChart ... />
</div>

// NEW (remove the h3 header):
<div className="p-5 rounded-xl bg-card border border-border/50 shadow-sm">
    <ForecastChart ... />
</div>
```

Then add the hidden-chart note immediately after the chart block:

```tsx
{/* Note when chart is hidden for Red confidence */}
{forecast.confidence_colour === 'Red' && (
    <p className="text-xs text-muted-foreground/60 text-center py-2">
        Chart unavailable for low-confidence forecasts
    </p>
)}
```

- [ ] **Step 8: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors. If `dirConfig` is referenced anywhere else, fix those references too.

- [ ] **Step 9: Fix existing page tests broken by the redesign**

Two tests in `frontend/src/app/forecast/__tests__/page.test.tsx` assert title-case text from the old badges row. The new `DirectionHeroCard` renders ALL-CAPS. Also, the `lucide-react` mock is missing `Lock` (used by `DirectionHeroCard`).

**In `page.test.tsx`, make these three changes:**

1. Add `Lock` to the `lucide-react` mock (line ~23):
```tsx
// OLD:
vi.mock('lucide-react', () => ({
    TrendingUp: ({ className }: any) => <span className={className}>TrendingUp</span>,
    TrendingDown: ({ className }: any) => <span className={className}>TrendingDown</span>,
    ArrowRight: ({ className }: any) => <span className={className}>ArrowRight</span>,
    AlertTriangle: ({ className }: any) => <span className={className}>AlertTriangle</span>,
    BarChart3: ({ className }: any) => <span className={className}>BarChart3</span>,
    Loader2: ({ className }: any) => <span className={className}>Loader2</span>,
    Info: ({ className }: any) => <span className={className}>Info</span>,
}))

// NEW (add Lock):
vi.mock('lucide-react', () => ({
    TrendingUp: ({ className }: any) => <span className={className}>TrendingUp</span>,
    TrendingDown: ({ className }: any) => <span className={className}>TrendingDown</span>,
    ArrowRight: ({ className }: any) => <span className={className}>ArrowRight</span>,
    AlertTriangle: ({ className }: any) => <span className={className}>AlertTriangle</span>,
    BarChart3: ({ className }: any) => <span className={className}>BarChart3</span>,
    Loader2: ({ className }: any) => <span className={className}>Loader2</span>,
    Info: ({ className }: any) => <span className={className}>Info</span>,
    Lock: ({ className }: any) => <span className={className}>Lock</span>,
}))
```

2. Line ~170 — `stale_banner_renders_when_is_stale` test: change the `waitFor` assertion:
```tsx
// OLD:
await waitFor(() => {
    expect(screen.getByText('Rising')).toBeInTheDocument()
})

// NEW:
await waitFor(() => {
    expect(screen.getByText('RISING')).toBeInTheDocument()
})
```

3. Line ~236 — `uncertain_badge_renders` test: change the final assertion:
```tsx
// OLD:
expect(screen.getByText('Uncertain')).toBeInTheDocument()

// NEW:
expect(screen.getByText('UNCERTAIN')).toBeInTheDocument()
```

- [ ] **Step 10: Run full test suite**

```bash
cd frontend && npx vitest run
```
Expected: all tests pass

- [ ] **Step 11: Commit**

```bash
git add frontend/src/app/forecast/page.tsx frontend/src/app/forecast/__tests__/page.test.tsx
git commit -m "feat(forecast): wire DirectionHeroCard and PriceRangeBar into forecast page"
```

---

## Final Verification

- [ ] **Start the dev server and manually check:**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000/forecast`, select a commodity + district and verify:
1. A large colored hero card appears with direction label (RISING / FALLING / STABLE)
2. Card background is emerald for Green, amber for Yellow, red for Red confidence
3. Price range bar shows below with Low/Mid/High track
4. Chart appears below (no header label)
5. For a Red confidence result: card shows UNCERTAIN, chart is hidden, note appears
6. Warning banners (stale/fallback) still appear above the hero card unchanged
