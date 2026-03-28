# Requirements: AgriProfit v2.0 — Farmer Intelligence ML Suite

**Defined:** 2026-03-08
**Core Value:** A farmer in any district can ask "what should I grow and when should I sell it?" and get a data-backed answer.

## v2.0 Requirements

### Crop Recommendation

- [ ] **CROP-01**: Farmer selects district and season, receives top 5 crops ranked by expected profit per hectare — integrating soil suitability score, yield model prediction, and price forecast
- [ ] **CROP-02**: Each recommended crop shows profit breakdown: expected yield (kg/ha), forecast price (Rs/quintal), estimated input cost, and net profit per hectare
- [ ] **CROP-03**: Next.js crop recommendation page with district/season selectors and ranked crop cards showing profit breakdown

### Sell vs Store

- [ ] **SELL-01**: For a commodity+district pair, system compares current price to 7/14/30-day forecast trajectory and produces a SELL NOW / HOLD / UNCLEAR signal with confidence indicator
- [ ] **SELL-02**: Break-even calculator shows storage duration, cost per quintal, forecast price gain, and net benefit — so farmer sees "Storing for X weeks costs Rs Y. Forecast gain is Rs Z. Net: Rs W"
- [ ] **SELL-03**: Next.js sell-vs-store page with commodity/district selector and decision card showing signal + break-even math

### Price Crash Warning

- [ ] **CRASH-01**: Rolling 7-day momentum anomaly detector flags when 3+ mandis drop >20% for the same commodity within a 7-day window
- [ ] **CRASH-02**: Frontend dashboard listing active crash warnings with commodity name, affected region, severity badge, and price trend mini-chart

### Sowing Window

- [ ] **SOW-01**: For a crop+district pair, system determines optimal planting month based on historical yield data cross-referenced with rainfall patterns and temperature data

### Fertilizer ROI

- [ ] **FERT-01**: Given a district's soil NPK deficit profile and the yield model, system calculates rupee gain per kg of N, P, and K fertilizer applied — showing diminishing returns curve

## Deferred (v3+)

- **SELL-STORAGE**: Commodity-category storage cost lookup table (perishable/semi-durable/durable) — v2 uses simplified estimate
- **CRASH-03**: Alert log DB table with historical crash signals for analytics
- **CRASH-04**: Historical crash pattern analysis showing past crash events and recovery timelines
- **CROP-SOIL**: Soil-aware exclusion of incompatible crops with fertilizer cost to fix deficiency — v2 uses existing soil advisor scores
- **SOW-02**: Weekly granularity sowing window (vs monthly in v2)
- **ARB-ALERT**: Automated daily arbitrage alert job (existing dashboard is sufficient for v2)

## Out of Scope

| Feature | Reason |
|---------|--------|
| LSTM price forecasting | Deferred to v3; XGBoost+Prophet baseline still being validated |
| Push notifications / SMS | Alert delivery mechanism deferred; v2 builds alert logic only |
| Field-level soil advice | No farm boundary or field-level soil data available |
| Real-time live price streaming | Agmarknet data arrives with 1-2 day lag |
| Chatbot / conversational advisor | Complexity-to-value ratio unfavorable per research |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CROP-01 | TBD | Pending |
| CROP-02 | TBD | Pending |
| CROP-03 | TBD | Pending |
| SELL-01 | TBD | Pending |
| SELL-02 | TBD | Pending |
| SELL-03 | TBD | Pending |
| CRASH-01 | TBD | Pending |
| CRASH-02 | TBD | Pending |
| SOW-01 | TBD | Pending |
| FERT-01 | TBD | Pending |

**Coverage:**
- v2 requirements: 10 total
- Mapped to phases: 0
- Unmapped: 10

---
*Requirements defined: 2026-03-08*
*Last updated: 2026-03-08 after initial definition*
