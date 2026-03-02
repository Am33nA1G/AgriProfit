# Requirements: AgriProfit ML Intelligence Platform

**Defined:** 2026-03-01
**Core Value:** A farmer in any district can ask "what should I grow and when should I sell it?" and get a data-backed answer.

## v1 Requirements

### Data Harmonisation

- [ ] **HARM-01**: System has a `district_name_map` table mapping all district name variants across the 4 datasets (prices, rainfall, weather, soil) with state-scoped fuzzy matching
- [ ] **HARM-02**: Price data is winsorised per commodity — corrupt outlier rows (CV > 500%) are flagged and capped before any feature or model computation
- [ ] **HARM-03**: Every price record can be joined to its rainfall district equivalent with >= 95% coverage (matching the 543/571 confirmed pairs)
- [ ] **HARM-04**: Every price record can be joined to its soil block equivalent for the 31 states with soil coverage

### Seasonal Price Calendar

- [ ] **SEAS-01**: User can select any of the 314 commodities and any state and see a monthly price chart (average +/- std) aggregated over the last 10 years
- [ ] **SEAS-02**: The calendar highlights the historically cheapest and most expensive months with labels ("Best time to sell", "Avoid selling")
- [ ] **SEAS-03**: Calendar shows data confidence — commodities/states with fewer than 3 years of data display a low-confidence warning
- [ ] **SEAS-04**: Calendar data is pre-aggregated and served from a `seasonal_price_stats` table (no ad-hoc full-table scans on the 25M row price table)

### Price Forecasting (XGBoost Baseline)

- [ ] **FORE-01**: System trains one XGBoost model per commodity using `ForecasterRecursiveMultiSeries` across all districts with >= 730 days of data
- [ ] **FORE-02**: Each model is validated using 4-fold walk-forward `TimeSeriesSplit` — RMSE and MAPE logged per fold before the model is accepted for serving
- [ ] **FORE-03**: User can request a 7-day and 14-day price forecast for any commodity+district combination with sufficient data
- [ ] **FORE-04**: Forecast response includes direction (up/down/flat), predicted range (not a point estimate), and a data-coverage tier label ("full model" / "seasonal average fallback")
- [ ] **FORE-05**: Commodity-district pairs with fewer than 365 days of data are automatically routed to the seasonal calendar fallback — not served an ML forecast
- [ ] **FORE-06**: Forecast results are cached in a `forecast_cache` PostgreSQL table and refreshed nightly via the existing APScheduler

### Feature Engineering

- [ ] **FEAT-01**: Lag features (7d, 14d, 30d, 90d price) and rolling statistics (7d/30d mean, std) are computed with strict `cutoff_date` enforcement — no look-ahead leakage
- [ ] **FEAT-02**: Monthly rainfall deficit/surplus vs 40-year average is computed as a feature for all 543 harmonised price-rainfall district pairs (Tier A)
- [ ] **FEAT-03**: Daily temperature and humidity features are available for the ~261 districts with weather coverage (Tier A+); remaining districts use rainfall-only features (Tier B)
- [ ] **FEAT-04**: Feature engineering functions are pure Python with unit tests — no database calls inside feature computation

### Soil Crop Advisor

- [ ] **SOIL-01**: User can select a state + district + block and see the soil health profile — N/P/K/OC/pH % distributions (high/medium/low) for the most recent cycle
- [ ] **SOIL-02**: System maps the block's deficiency profile to a ranked list of suitable crops using ICAR crop-soil requirement thresholds
- [ ] **SOIL-03**: Every recommendation displays "Block-average soil data for [block name] — not field-level measurement" to prevent misleading farmers
- [ ] **SOIL-04**: Fertiliser advice is generated per nutrient deficiency (e.g. "73% of soils in this block are nitrogen-deficient — consider urea application before planting")
- [ ] **SOIL-05**: Coverage gap is explicit in the UI — soil advisor is labelled "Available for 31 states" with a map showing covered vs uncovered regions

### Mandi Arbitrage Dashboard

- [ ] **ARB-01**: User can select a commodity and origin district and see the top 3 destination mandis ranked by net profit after freight + spoilage (using the existing transport engine)
- [ ] **ARB-02**: Arbitrage signals are only shown when net margin after transport exceeds a configurable threshold (default: 10% of commodity modal price)
- [ ] **ARB-03**: Dashboard only displays data fresher than 7 days — stale data is flagged rather than shown as current
- [ ] **ARB-04**: Each arbitrage result shows distance (km), travel time, freight cost, spoilage estimate, and net expected profit per quintal

### ML Serving Infrastructure

- [ ] **SERV-01**: FastAPI exposes `/api/v1/forecast/{commodity}/{district}`, `/api/v1/seasonal/{commodity}/{state}`, `/api/v1/soil-advisor/{state}/{district}/{block}`, and `/api/v1/arbitrage/{commodity}/{district}` endpoints
- [ ] **SERV-02**: Trained models are loaded at FastAPI startup via the existing lifespan pattern into `app.state.models` — model files live in `ml/artifacts/`
- [ ] **SERV-03**: Model loading uses an LRU cache with configurable memory limit — models are lazy-loaded on first request, not all at startup
- [ ] **SERV-04**: APScheduler runs nightly forecast refresh job — stale forecasts are regenerated, new price data since last refresh is incorporated

### Frontend Dashboards

- [ ] **UI-01**: Seasonal price calendar page — commodity + state selector, monthly bar/line chart, best/worst month highlights
- [ ] **UI-02**: Price forecast page — commodity + district selector, 14-day forecast chart with confidence band, tier label, data coverage indicator
- [ ] **UI-03**: Soil advisor page — state -> district -> block drill-down, NPK/pH distribution bars, crop recommendation list, fertiliser advice cards
- [ ] **UI-04**: Arbitrage dashboard — commodity + origin district selector, ranked mandi table with net profit, distance, freshness indicator
- [ ] **UI-05**: All dashboards display coverage gap messages when a feature is unavailable for the selected region (no silent failures)

## v2 Requirements

### LSTM Ensemble (deferred — requires XGBoost baseline validated first)

- **LSTM-01**: LSTM model trained for high-volatility commodities (onion, tomato, potato — CV > 20%) using 60-day input sequences
- **LSTM-02**: LSTM only deployed where it beats XGBoost baseline by >5% RMSE on holdout — otherwise XGBoost remains
- **LSTM-03**: Scheduled weekly retraining for LSTM models with drift detection

### Live Price Integration (deferred)

- **LIVE-01**: Existing data.gov.in API client wired to refresh forecasts when new price data arrives (event-driven rather than nightly batch)

### Mobile Parity (separate project — already complete)

- **MOB-01**: All ML features available in the React Native mobile app (AgriProfit Mobile — separate completed project)

## Out of Scope

| Feature | Reason |
|---|---|
| Crop yield prediction | No production volume data (area planted, tonnes harvested) — data physically missing |
| MSP / policy impact modeling | No government policy event timeline — data physically missing |
| Field-level soil advice | Only block-level aggregate distributions available — claiming field-level accuracy would be harmful |
| Real-time live prices | API client exists but event-driven ML refresh is v2 complexity |
| Separate ML microservice | Project constraint: Python ML served via existing FastAPI — no new services |
| Crop disease detection | No image data, no IoT sensors |

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| HARM-01 | Phase 1 | Pending |
| HARM-02 | Phase 1 | Pending |
| HARM-03 | Phase 1 | Pending |
| HARM-04 | Phase 1 | Pending |
| SEAS-01 | Phase 2 | Pending |
| SEAS-02 | Phase 2 | Pending |
| SEAS-03 | Phase 2 | Pending |
| SEAS-04 | Phase 2 | Pending |
| UI-01 | Phase 2 | Pending |
| FEAT-01 | Phase 3 | Pending |
| FEAT-02 | Phase 3 | Pending |
| FEAT-03 | Phase 3 | Pending |
| FEAT-04 | Phase 3 | Pending |
| FORE-01 | Phase 4 | Pending |
| FORE-02 | Phase 4 | Pending |
| FORE-03 | Phase 4 | Pending |
| FORE-04 | Phase 4 | Pending |
| FORE-05 | Phase 4 | Pending |
| FORE-06 | Phase 4 | Pending |
| SERV-01 | Phase 4 | Pending |
| SERV-02 | Phase 4 | Pending |
| SERV-03 | Phase 4 | Pending |
| SERV-04 | Phase 4 | Pending |
| UI-02 | Phase 4 | Pending |
| SOIL-01 | Phase 5 | Pending |
| SOIL-02 | Phase 5 | Pending |
| SOIL-03 | Phase 5 | Pending |
| SOIL-04 | Phase 5 | Pending |
| SOIL-05 | Phase 5 | Pending |
| UI-03 | Phase 5 | Pending |
| ARB-01 | Phase 6 | Pending |
| ARB-02 | Phase 6 | Pending |
| ARB-03 | Phase 6 | Pending |
| ARB-04 | Phase 6 | Pending |
| UI-04 | Phase 6 | Pending |
| UI-05 | Phases 2-6 | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0 (complete coverage confirmed)

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 — traceability confirmed against 6-phase roadmap*
