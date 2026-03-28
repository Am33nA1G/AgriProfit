# Forecast Page Redesign — Design Spec
**Date:** 2026-03-10
**Status:** Approved

## Goal
Farmers (primary users) need to answer one question at a glance: **"Is the price going up or down?"** The current page buries the answer in small badge chips. This redesign surfaces direction + confidence as the dominant visual element.

## User Context
- Primary user: farmers
- Device: mobile and desktop (mobile-first)
- Core need: trend direction with confidence signal

---

## Design: Option A — Direction Hero Card

### Layout Structure (top → bottom)

1. Header (unchanged)
2. Selectors row (unchanged)
3. Warning banners (stale data / fallback / low-confidence) — unchanged, stay at top
4. **Direction Hero Card** ← new focal point
5. Price Range Row
6. Forecast Chart (full width)
7. Footer metadata (unchanged)

---

### 1. Direction Hero Card

A full-width rounded card. Background tint + border color encodes confidence; icon + text encodes direction.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   ↑ (48px icon)    RISING                          │
│                    Prices expected to rise          │
│                    over the next 7 days             │
│                                                     │
│   [Reliable · ±12%]   [v5 · LightGBM]  [R² 0.84] │
└─────────────────────────────────────────────────────┘
```

**Color mapping:**

| Confidence | Background     | Border          | Icon/Text      |
|------------|----------------|-----------------|----------------|
| Green      | `emerald-50`   | `emerald-200`   | `emerald-700`  |
| Yellow     | `amber-50`     | `amber-200`     | `amber-700`    |
| Red        | `red-50`       | `red-200`       | `red-700`      |

**Direction labels:**
- `up` → `↑` TrendingUp icon + "RISING" + "Prices expected to rise over the next N days"
- `down` → `↓` TrendingDown icon + "FALLING" + "Prices expected to fall over the next N days"
- `flat` → `→` ArrowRight icon + "STABLE" + "Prices holding steady over the next N days"
- `uncertain` (or Red confidence) → lock icon + "UNCERTAIN" + "Do not use for financial decisions"

**Technical badges** (model version, R², confidence pill) sit at the bottom of the card in `text-xs text-muted-foreground` — visible but not competing for attention.

---

### 2. Price Range Row

A horizontal range visualizer replacing the plain price card:

```
Low              Mid              High
₹420  ●────────────●────────────●  ₹590
                ₹510
```

- Thin horizontal track with three dots
- Mid dot is larger and bolder
- Mobile fallback: simple 3-column grid (Low / Mid / High)

---

### 3. Forecast Chart

- Remove redundant "Forecast Chart" section header (self-evident)
- Keep Red-confidence gate (chart hidden for Red)
- Add note when chart is hidden: *"Chart unavailable for low-confidence forecasts"*

---

## What Does NOT Change
- Selectors (commodity / state / district / horizon)
- Warning banners (stale, fallback, low-confidence)
- Footer metadata (n_markets, last_data_date, typical_error_inr)
- Backend API — frontend-only change

---

## Files to Modify
- `frontend/src/app/forecast/page.tsx` — replace badges row + price card with new components
- New component: `frontend/src/components/DirectionHeroCard.tsx`
- New component: `frontend/src/components/PriceRangeBar.tsx`
