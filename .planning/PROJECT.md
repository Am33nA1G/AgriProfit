# AgriProfit — Agricultural Intelligence Platform

## What This Is

AgriProfit is a farmer-facing intelligence platform that turns 10 years of APMC market prices, 40 years of rainfall, 10 years of daily weather, and block-level soil health data (NPK/pH) into actionable signals: price forecasts, crop recommendations by soil profile, seasonal sell windows, and cross-mandi arbitrage alerts. It sits on top of an existing FastAPI + PostgreSQL + Next.js platform with a working transport logistics engine.

## Core Value

A farmer in any district can ask "what should I grow and when should I sell it?" and get a data-backed answer — not a guess.

## Current Milestone: v2.0 Farmer Intelligence ML Suite

**Goal:** Give farmers actionable, data-backed decisions on what to grow, when to sell, when to apply fertilizer, and where to sell — integrating all existing ML models, data, and transport modules into unified intelligence features.

**Target features:**
- Crop Recommendation Engine (soil + yield + price forecast → optimal crop selection per district)
- Sell vs Store Decision Engine (price forecast + storage cost → hold/sell signal)
- Price Crash Early Warning (anomaly detection on price momentum → alert system)
- Optimal Sowing Window Predictor (yield + rainfall + weather → best planting period)
- Fertilizer ROI Calculator (soil nutrient gap + yield model → ₹ ROI per kg fertilizer)
- Cross-Mandi Arbitrage Alerts (automated daily alerts enhancing v1 dashboard)

## Requirements

### Validated

<!-- v1.0 shipped — all 6 phases complete, 16/16 plans executed. -->

- ✓ FastAPI backend with SQLAlchemy + PostgreSQL + Alembic — existing
- ✓ Next.js frontend — existing
- ✓ Transport logistics engine (freight, spoilage, risk, OSRM routing) — v1.0
- ✓ Data sync infrastructure (APScheduler + data.gov.in API client) — existing
- ✓ 25.1M rows Agmarknet daily prices (2015–2025) loaded in DB + parquet — existing
- ✓ 598 passing tests — existing
- ✓ OTP authentication + JWT session management — existing
- ✓ Role-based access (user / admin) — existing
- ✓ District harmonisation across prices, rainfall, weather, soil — v1.0 Phase 1
- ✓ Seasonal price calendar (314 commodities, 10yr aggregation) — v1.0 Phase 2
- ✓ Feature engineering foundation (price lags, rainfall, weather, soil) — v1.0 Phase 3
- ✓ XGBoost + Prophet price forecasting + serving — v1.0 Phase 4
- ✓ Soil crop advisor (ICAR rule-based, 21 states) — v1.0 Phase 5
- ✓ Mandi arbitrage dashboard (transport-integrated, net profit ranking) — v1.0 Phase 6
- ✓ Harvest advisor module (yield RF models, weather warnings, crop calendar) — existing
- ✓ Crop yield models (RandomForest, 6 categories, 102 crops, 230K training rows) — existing

### Active

<!-- v2.0 Farmer Intelligence ML Suite — building toward these. -->

- [ ] Crop recommendation engine — integrated soil + yield + price forecast → ranked crop list with expected profit/ha
- [ ] Sell vs store decision engine — price forecast trajectory + storage cost model → daily hold/sell signal per commodity
- [ ] Price crash early warning — rolling momentum anomaly detection → alert when ≥3 mandis drop >20% in 7 days
- [ ] Optimal sowing window predictor — yield history + rainfall pattern + temperature → best planting week per crop-district
- [ ] Fertilizer ROI calculator — soil nutrient counterfactual via yield model → ₹ gain per kg fertilizer applied
- [ ] Cross-mandi arbitrage alerts — automated daily alerts for price spreads exceeding transport cost threshold

### Out of Scope

- LSTM price forecasting — deferred to v3; XGBoost+Prophet baseline still being validated
- MSP / policy impact modeling — no government policy event timeline data
- Real-time live prices — API sync exists but live ML inference not yet warranted
- React Native mobile — separate completed project
- Individual farm-level advice — no farm boundary or field-level soil data
- Push notifications / SMS alerts — alert delivery mechanism deferred; v2 builds alert logic only

## Context

### Data Assets (all in C:\Users\alame\Desktop\repo-root\data\)

| Dataset | Rows | Coverage | Format |
|---|---|---|---|
| Agmarknet daily prices | 25.1M | 314 commodities, 32 states, 571 districts, 2015–2025 | PostgreSQL + parquet |
| Soil health (NPK/pH) | 84,794 | 31 states, 731 districts, 6,895 blocks, 3 cycles | parquet |
| Rainfall monthly | 306,646 | 33 states, 616 districts, 1985–2026 | parquet |
| Weather daily | 1,095,442 | 290 districts, 2016–2025 (split across 2 CSVs) | CSV |

### Cross-dataset Join Quality

| Join | Exact match | After fuzzy |
|---|---|---|
| Price ↔ Rainfall | 543/571 (95%) | ~560 |
| Price ↔ Soil | 464/571 (81%) | ~488 |
| Price ↔ Weather | 237/571 (41%) | ~261 |

### Key Data Insights

- Tomato seasonal CV = 34%, Onion = 26%, Wheat = 2% — high vegetable volatility makes ML valuable
- 69.7% of blocks nationwide are LOW in Nitrogen; 86.9% LOW in pH — soil deficiency is widespread
- Soil data missing only for Chandigarh, Delhi NCT, Puducherry (tiny UTs, negligible farmland)
- Weather data only covers ~46% of price districts after fuzzy matching — tiered feature strategy needed

### Tech Stack for ML Layer

- Python: pandas, scikit-learn, XGBoost, statsmodels, PyTorch (LSTM)
- Models: serialised to disk (joblib/torch.save), loaded by FastAPI at startup
- New DB tables: `district_name_map`, `seasonal_price_stats`, `forecast_cache`, `soil_crop_suitability`
- New Alembic migrations for each new table

## Constraints

- **Tech stack**: Python ML models served via existing FastAPI — no new microservices
- **Database**: PostgreSQL only — no separate vector DB or feature store for v1
- **Coverage**: Soil recommendation available only for 31 states; weather features only for ~260 districts — UI must communicate coverage gaps
- **Data freshness**: Price data ends 2025-10-30; forecasts are retrospective validation + near-term projection, not live
- **Performance**: Price data is 25M rows — all queries MUST include date filters; full-table scans cause 60s+ timeouts (learned from existing transport engine work)

## Key Decisions

| Decision | Rationale | Outcome |
|---|---|---|
| XGBoost before LSTM | Tabular model is faster to train, validate, and serve; provides baseline to beat | — Pending |
| District fuzzy matching as Phase 1 | All cross-dataset features depend on this; must unlock before any ML | — Pending |
| Seasonal calendar as first user-facing feature | Pure aggregation, zero model risk, immediate farmer value | — Pending |
| Block-level soil distributions (not field-level) | Only available granularity; must communicate as "block average" to users | — Pending |
| Tiered weather coverage | 260/571 districts have weather; use rainfall for the rest rather than dropping rows | — Pending |

---
*Last updated: 2026-03-08 after v2.0 milestone start*
