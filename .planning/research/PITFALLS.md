# Domain Pitfalls: Agricultural Price Forecasting ML

**Domain:** Agricultural intelligence platform — price forecasting, crop recommendation, seasonal analytics
**Researched:** 2026-03-01
**Confidence:** HIGH (verified against actual data files; pitfalls confirmed empirically, not hypothetically)

---

## Critical Pitfalls

These mistakes cause model rewrites, misleading farmer advice, or silent data corruption that goes undetected until production.

---

### Pitfall 1: Price Unit Confusion Corrupting All Models

**What goes wrong:** The Agmarknet dataset contains prices in two different units: rupees per quintal (most rows) and rupees per kg (some rows, typically < 200). The existing codebase already normalizes prices < 200 by multiplying by 100. However, there are also 251 records priced above 1 million, 3 above 10 million, and one at 6.875 × 10^17 — values that are obviously data entry errors (extra zeros, wrong decimal placement). These extreme outliers, if not filtered before training, will corrupt the entire model because XGBoost and LSTM both treat extreme values as valid signal.

**Evidence from data:** Actual inspection of `agmarknet_daily_10yr.parquet` shows CV% for Guar = 23,284%, Cumin Seed = 22,214%, Bajra = 9,413% — mathematically impossible volatility caused entirely by a handful of corrupt rows mixed into 25M rows. A model trained on this produces predictions spanning multiple orders of magnitude.

**Why it happens:** APMC reporting is manual entry by mandi staff. Common errors include: copying the wrong column (entering per-kg price in per-quintal field), extra trailing zeros, and unit switching across reporting cycles.

**Consequences:** Every model trained on raw prices will have corruption baked in. The corruption is invisible in aggregates (mean/std look reasonable at district level). Silent failure — the model trains without error, produces nonsensical predictions only discovered when a farmer sees a "forecast" of ₹500 crore per quintal.

**Prevention:**
- Apply winsorization per commodity before any feature engineering: cap prices at `median × 20` (or use IQR × 3 as the outer fence). Do NOT use global winsorization — commodity price ranges differ by 100x.
- Validate that after winsorization, CV% for any commodity-district pair is < 200%. If it exceeds this, flag the pair for manual review before training on it.
- Store the winsorization bounds per commodity in a `price_bounds` table so the same bounds apply at inference time.
- Log every capped value to an audit table.

**Detection (warning signs):**
- Training loss refuses to converge (extreme outlier dominates gradient)
- Model predictions span multiple orders of magnitude for the same commodity
- Validation RMSE is > 5x the interquartile range of the training prices

**Phase:** Data harmonisation (Phase 1). This MUST be resolved before any modelling phase.

---

### Pitfall 2: Data Leakage via Look-Ahead Bias in Feature Engineering

**What goes wrong:** Look-ahead bias contaminates any feature that uses information unavailable at prediction time. For this project, the two specific traps are:

**Trap A — Rainfall as an exogenous price feature:** Monthly rainfall data for month M is only fully known after month M ends. If rainfall for October 2024 is used to predict October 2024 prices, the model sees the future. At inference time in early October, that rainfall value does not exist. The correct approach: use rainfall for month M-1 (lagged one full month) as the input feature.

**Trap B — Rolling statistics crossing the train/test boundary:** If you compute a 30-day rolling mean price before splitting into train/test, the rolling mean for the first 30 days of the test set incorporates prices from the training set — this leaks future information into what appears to be historical context. Rolling statistics must be computed within each fold of walk-forward validation, never on the full dataset first.

**Trap C — Target encoding with insufficient grouping:** If the model uses mean historical price per commodity-district as a feature, and that mean is computed on the full dataset before splitting, the training rows "know" their own contribution to the test mean — a subtle but real form of leakage.

**Why it happens:** Pandas `.rolling()` and `.shift()` operations on a full DataFrame are the most common cause. Developers run `df['lag7'] = df.groupby(['commodity','district'])['price'].shift(7)` on the whole dataset before calling train_test_split, which is correct — but then run `df['rolling30'] = df.groupby(['commodity','district'])['price'].rolling(30).mean()` which is wrong because it uses data that straddles the split point.

**Consequences:** Model metrics appear excellent (RMSE 10–30% better than reality). Model fails in production because the features it relied on are unavailable at prediction time. Research papers on agricultural price forecasting frequently report suspiciously high accuracy — a 2025 study on implied volatility forecasting directly attributed performance inflation to this exact mechanism.

**Prevention:**
- Implement a strict `TimeSeriesPipeline` class that wraps all feature engineering steps. Feature computation must accept a `cutoff_date` parameter and only use data `< cutoff_date`.
- For rainfall features: always shift by at least 1 month. For weather features (temperature, humidity): shift by at least 1 day.
- Use `sklearn.pipeline.Pipeline` with custom transformers that enforce the cutoff. Never compute rolling features outside the pipeline.
- Add a leakage detection test: train on years 1–7, test on year 8. Manually inspect whether any feature value for a test row was computed using test-period data.

**Detection (warning signs):**
- Walk-forward validation RMSE is 2–5x higher than simple train/test RMSE (gap indicates leakage in train/test evaluation)
- Model performance degrades sharply at the first prediction after a train cutoff
- Feature importance shows exogenous lag-0 features (same-day weather, same-month rainfall) as top predictors

**Phase:** Feature engineering phase (Phase 3). Build the `TimeSeriesPipeline` abstraction before writing any feature code.

---

### Pitfall 3: Train/Test Split Instead of Walk-Forward Validation

**What goes wrong:** A random 80/20 train/test split on time series data violates temporal ordering — the model trains on rows from 2023 while validating on rows from 2019. This produces optimistically biased metrics because it leaks seasonal patterns and long-term trends that the model "shouldn't know" at prediction time. The correct approach is walk-forward validation (also called expanding-window cross-validation): train on all data through year N, validate on year N+1, retrain through N+1, validate on N+2, and so on.

**Why it happens:** `sklearn.model_selection.train_test_split` is the default in all ML tutorials. It works correctly for i.i.d. data; it silently fails for time-series.

**Consequences:** XGBoost models validated with random split will show RMSE of X, then achieve RMSE of 3–5X in production. The model "cheated" by seeing price patterns from after its supposed knowledge cutoff. For agricultural price forecasting specifically, this is critical because prices have strong annual seasonality — a model that trains on October 2023 and validates on October 2019 implicitly learns the October seasonal shape, which masks whether it can genuinely predict October prices from features alone.

**The right approach:** For this project with 10 years of data (2015–2025):
- Fold 1: Train 2015–2020, validate 2021
- Fold 2: Train 2015–2021, validate 2022
- Fold 3: Train 2015–2022, validate 2023
- Fold 4: Train 2015–2023, validate 2024
- Report average RMSE across all 4 folds. Use this, not a single split, to select hyperparameters.

**Prevention:**
- Use `sklearn.model_selection.TimeSeriesSplit` or implement custom walk-forward logic.
- Enforce a minimum gap of 30 days between the last training row and first validation row to avoid leakage from rolling features.
- Never use `shuffle=True` anywhere in the data pipeline.

**Detection:** If validation RMSE is better than training RMSE, you have leakage or incorrect split ordering.

**Phase:** Evaluation infrastructure must be built in Phase 2 (XGBoost baseline) before any hyperparameter tuning.

---

### Pitfall 4: Policy Discontinuities Breaking Model Assumptions

**What goes wrong:** Agricultural price models assume stationarity — that the statistical relationship between features and prices is stable over time. India has multiple documented policy events that create structural breaks, where this assumption catastrophically fails:

| Event | Date | Effect |
|-------|------|--------|
| Demonetisation | Nov 8, 2016 | Cash shortages → immediate price shock across all mandis. Employment contracted 2%+, credit contracted 2%+ in Q4 2016. |
| GST rollout | Jul 1, 2017 | Supply chain disruption, logistics cost changes |
| COVID-19 lockdown | Mar 24, 2020 | Market closures, mandi data gaps, transport suspension |
| Onion export ban | Multiple years (2010, 2011, 2013, 2019, 2022) | Domestic price crash within weeks of ban announcement |
| Rice export restrictions | 2022–2025 | International price floor removed, domestic surplus |
| Tomato/vegetable inflation | Jul–Aug 2023 | Supply shock from unseasonal rains |

A model trained on 2015–2019 and applied to 2020–2021 will predict as if COVID did not happen. A model that includes 2020 training data will partially "learn" that COVID-era relationships are normal.

**Why it happens:** No event calendar is included in the dataset. The model sees price anomalies but has no feature explaining why they occurred.

**Consequences:** Models extrapolate pre-break relationships into post-break periods. Forecast confidence intervals do not widen appropriately around structural break periods. A farmer told "onion price will be ₹2000/q in Nov" based on a model trained pre-export-ban will face actual prices of ₹600/q.

**Prevention:**
- Create a `policy_events` table with (date, event_type, commodity_affected, impact_direction) — even a minimal version with 10–15 known events.
- Add a `days_since_nearest_event` feature to the model input.
- Train separate model versions: pre-2020 (structural break-free), post-2020 (includes COVID regime), and evaluate which performs better on recent data.
- In forecast UI, show a "model uncertainty is elevated" warning for forecasts within 90 days of any recorded policy event.
- Flag forecasts as LOW CONFIDENCE for commodities/districts where the most recent training data includes a structural break period.

**Note:** MSP / policy impact modeling is explicitly out of scope per PROJECT.md. However, an events calendar is still achievable without modeling MSP causally — it simply marks periods where the model's assumptions are weaker.

**Detection:** Walk-forward validation folds that include 2016 or 2020 will show dramatically higher RMSE than folds that don't. If fold 2020–2021 RMSE is > 3x the average of other folds, the model is not handling discontinuities.

**Phase:** Data harmonisation (Phase 1) — add policy events table. Evaluation framework (Phase 2) — flag fold performance by year.

---

### Pitfall 5: District Name Harmonisation Cascade Errors

**What goes wrong:** The four datasets (prices, rainfall, soil, weather) use different spellings, capitalizations, and transliterations for the same Indian districts. Known examples from this specific domain:

- "Karimnagar" vs "Karimanagar" (single character swap)
- "Banaskantha" vs "Banas Kantha" (spacing difference)
- "Laxmi" vs "Lakshmi" (Hindi romanization variant)
- "Ahmedabad" vs "Ahmadabad" (vowel variant)
- Districts that have been bifurcated since data collection started (Telangana split from AP in 2014 — prices data spans both pre and post-split)

**Cascade failure mechanism:** Generic fuzzy matching (Levenshtein distance) with a single global threshold will create false matches. A false match in early matching removes a record from the pool; subsequent matches then find the next-closest string, which may be a different false match. This was empirically measured: generic tools like Stata's `reclink` achieve only 47.5% accuracy on Hindi district names versus 93.1% for state-scoped, culturally-aware matching.

**Current project exposure:** The join table in PROJECT.md shows Price ↔ Soil at 81% exact match (464/571 districts). The remaining 107 districts (19%) need fuzzy matching. Even 1% cascade error in a 571-district dataset means ~6 districts silently mapped to the wrong state — meaning soil NPK data for, say, Nashik ends up attributed to a district in a different state.

**Why it happens:** The impulse to run one fuzzy match pass over all records at once, accept all matches above a threshold, and move on. The correct approach requires manual review of every match that falls in a "gray zone" confidence band.

**Prevention:**
- Always scope fuzzy matching within state boundaries. Never match across states.
- Use a three-tier matching strategy:
  1. Exact string match (accept all)
  2. Fuzzy match within same state (accept only if score > 0.90, review 0.75–0.90)
  3. Manual review for anything below 0.75
- Build the `district_name_map` table with a `match_type` column: `exact`, `fuzzy_accepted`, `manual`, `unmatched`.
- For every fuzzy match, store both the source name and target name for human review.
- Never silently drop unmatched districts — the 107 unmatched price↔soil districts represent substantial farmland; log them explicitly.
- Do not trust LGD (Local Government Directory) codes from one dataset to join another — coding schemes changed in 2018-2020 during state reorganisations.

**Detection (warning signs):**
- A district appears in rainfall data but not in price data for a state that clearly has both (e.g., coastal Maharashtra with documented mandis)
- After joining, any district shows impossible cross-dataset correlations (rainfall stats appropriate for a different climate zone)
- `district_name_map` table has matches where state_source != state_target

**Phase:** Phase 1 (district harmonisation). This is the foundation — all ML features depend on correct joins. No model should be trained until harmonisation is validated and the `district_name_map` table is reviewed by at least spot-checking 20 manually selected matches.

---

### Pitfall 6: Soil Recommendation Presenting Block Averages as Field-Level Precision

**What goes wrong:** The soil health data in this project is a percentage distribution — for each block and nutrient, it records what percentage of sampled fields are High/Medium/Low. Example from the actual data:

```
block: CAMPBELL BAY - 6498
nutrient: Nitrogen
high: 0.0, medium: 92.0, low: 8.0
```

This means: "of all fields sampled in this block, 0% had high N, 92% had medium N, 8% had low N." It does NOT mean any specific field has medium nitrogen. A farmer in this block might be in the 8% who have low nitrogen — the recommendation to "add moderate N" based on the 92% majority is actively harmful for that farmer.

**Why it happens:** The data schema looks like it contains soil values per block. Developers (and users) naturally interpret "block = geographic unit with soil data" as "the soil in this block has these properties," not "this block has a distribution of soil properties."

**The actual data confirms this:** The soil parquet schema is `(cycle, state, district, block, nutrient, high, medium, low)` where high+medium+low = 100%. It is explicitly a statistical distribution, not a measurement.

**Consequences:** A farmer receives a crop recommendation based on "your block's soil is typically medium-nitrogen" when their specific field may be severely deficient. The platform creates false confidence that could lead farmers to underinvest in inputs — a direct harm.

**Prevention:**
- In the UI layer, ALWAYS display soil data with the distribution, not a single value. Show: "In your block (Campbell Bay), 92% of fields have medium nitrogen. Your field may differ — get a soil test."
- Never convert the distribution to a single label (e.g., "Medium Nitrogen") for display. Show the percentages.
- Add a "Confidence" column to soil recommendations: `block_sample_size` and `dominant_category_pct`. A block where 95% of fields are "Low" is more reliably "low" than one where 40%/35%/25% are spread across three categories.
- Include a disclaimer on every soil recommendation page: "Based on government soil survey data (block-level average, not your specific field). For precise advice, request a Soil Health Card from your local Krishi Vigyan Kendra."
- Log every soil recommendation for audit. If coverage gaps are later identified (soil data missing for 3 UTs), surface a "No soil data available for your district" message, not a fallback recommendation.

**Detection:** If the recommendation UI shows a single soil status per nutrient (e.g., "Nitrogen: Medium") without any distribution or uncertainty information, the pitfall has been triggered.

**Phase:** Crop recommendation engine (Phase 5). Build the UI schema to show distributions from day one — retrofitting this after launch requires a UI rewrite.

---

## Moderate Pitfalls

### Pitfall 7: Sparse Commodity-District Pairs — Modelling Where Insufficient Data Exists

**What goes wrong:** Of the 19,679 commodity-district pairs in the data, 4,875 (24.8%) have fewer than 365 rows — less than one year's worth of daily data. Only 8,591 pairs (43.7%) have 3+ years of data. Training an XGBoost or LSTM model on fewer than 365 daily observations is insufficient to learn seasonal patterns. An LSTM with sequences of length 30 trained on 365 rows has only ~12 non-overlapping sequences — almost guaranteed overfitting.

**Prevention:**
- Define a minimum data threshold before training: 730 days (2 years) for XGBoost, 1095 days (3 years) for LSTM.
- For sparse pairs (fewer than 730 days), fall back to the seasonal calendar (aggregated statistics) rather than a ML forecast. The UI should surface a "historical average" rather than a model prediction.
- Never train a separate model per commodity-district pair for sparse pairs. Consider hierarchical models: share parameters across similar commodities or districts, train at the state-commodity level and personalize with local offsets.
- Add a `model_coverage` table that records for each (commodity, district): data count, first date, last date, model type assigned (full ML / seasonal average / insufficient data).

**Detection:** Training pipeline completes without error for all 19,679 pairs but validation metrics are unrealistically good for sparse pairs (overfitting on < 100 sequences).

**Phase:** XGBoost baseline (Phase 2). Apply the threshold filter before the training loop.

---

### Pitfall 8: Serving 314 Commodity Models — Memory Multiplication

**What goes wrong:** If all commodity-district XGBoost models (potentially 8,000–10,000 separate `.joblib` files for pairs with sufficient data) are loaded at FastAPI startup, memory consumption is prohibitive. With Gunicorn's multiple workers, each worker loads all models independently — confirmed by the FastAPI GitHub discussion #7069 — multiplying RAM by worker count. A 1.5 GB model set with 4 workers = 6 GB RAM.

**Prevention:**
- Use lazy loading: load a model only on first request for that commodity-district. Cache it in a process-level dict. Evict least-recently-used models via an LRU cache when the total loaded set exceeds a memory limit (e.g., 2 GB).
- If using Gunicorn with `--preload`, models loaded before worker fork share memory via copy-on-write. But note: PyTorch models (LSTM) may experience forking-related issues — test explicitly.
- For LSTM models specifically (per-commodity, trained for volatile commodities), keep only the 5–10 most-requested models warm. Load others from disk on demand.
- Add a `/health` endpoint that reports `models_loaded_count` and `models_cache_memory_mb`. Alert if cache exceeds threshold.
- Store model metadata (path, last loaded timestamp, request count) in a `model_registry` table in PostgreSQL rather than loading from a flat directory. This makes the available model inventory queryable.

**Detection:** Worker RSS memory climbs monotonically over days without releasing; `top` shows FastAPI worker processes each consuming > 1 GB.

**Phase:** ML serving endpoints (Phase 6). Design the model registry and LRU cache before writing any `/forecast` endpoint.

---

### Pitfall 9: Missing Mandi Days — Naive Lag Features Encoding Gaps as Signal

**What goes wrong:** Agmarknet data is not daily for every mandi. A mandi closed on a festival, market holiday, or reporting gap will have a missing row for that day. If you create `lag_1 = price.shift(1)` without handling gaps, the lag for a Monday row after a Sunday closure points to Saturday — a 2-day gap — but the model treats it as a 1-day lag. After a 90-day data gap, `lag_7` returns a price from a different season entirely. The 12,320 commodity-district pairs that have at least one 90-day gap in the data are particularly vulnerable.

**Prevention:**
- Create a complete daily time series grid for each commodity-district pair (filling gaps with NaN), then compute lags on the grid.
- Use `price_days_since_last_observation` as an explicit feature. The model then learns that a price after a long gap is less correlated with the "lag_1" value.
- For XGBoost: XGBoost handles NaN natively by learning to route NaN to the appropriate branch. This is generally correct behaviour, but only if NaN means "missing" not "zero" — never fill gaps with zero.
- For LSTM: NaN in sequences breaks training. Options: (a) remove sequences containing any NaN, (b) use masking layers. For this project, option (a) is safer at the cost of fewer training examples.

**Detection:** Feature importance shows `lag_1` as the dominant predictor even for commodities with many data gaps (the model is picking up gap artifacts as strong signal).

**Phase:** Feature engineering (Phase 3). The grid reindexing step must be the first transformation before any lag calculation.

---

### Pitfall 10: Weather Coverage Gap — Silently Degrading Model Quality for 54% of Districts

**What goes wrong:** Weather data (temperature, humidity) covers only ~260 of 571 districts (45.5%). If you include weather features in a unified model and impute missing weather with mean/median for uncovered districts, you create a systematic bias: the model learns weather patterns from covered districts, then applies them to uncovered districts using imputed (wrong) values. The model appears to use weather features everywhere, but for 55% of districts it is using noise disguised as signal.

**Prevention:**
- Maintain two distinct model tiers, explicitly:
  - Tier A: Weather-covered districts (~260) — use weather + rainfall + price lags
  - Tier B: Rainfall-only districts (~300) — use rainfall + price lags only
- Never impute missing weather with global means. Imputing temperature from a national average destroys the feature's value entirely.
- In the UI, display a "Data quality" badge per forecast: "Full model (weather + rainfall)" vs "Partial model (rainfall only)."
- Test that Tier B districts show comparable validation metrics to Tier A districts on rainfall-only features — if not, the baseline rainfall model is underpowered.

**Detection:** Tier B district forecasts have higher RMSE than Tier A, but no systematic bias. If Tier B shows lower RMSE (after imputation), imputed values are leaking signal.

**Phase:** Weather-enhanced model (Phase 4). Build Tier A/B split from the start, not as a retrofit.

---

### Pitfall 11: Seasonal Calendar Distorted by COVID-Era Data and Outliers

**What goes wrong:** The seasonal price calendar ("best month to sell commodity X in state Y") is built by aggregating 10 years of daily prices into monthly statistics. If outlier months are not handled, the 2020 COVID crash months will drag down March–May averages, and the 2023 tomato price spike will inflate August averages — making the historical calendar misleading as a "typical" expectation.

**Prevention:**
- Use median price by month, not mean. The median is robust to outliers (COVID months, price spikes).
- Compute calendar on 2015–2019 data and 2021–2025 data separately; if the two periods differ by > 20% for any month, flag that month as "historically variable."
- Apply minimum observation threshold per month: require at least 30 price observations for a given commodity-state-month combination before displaying a seasonal estimate. Below this, show "insufficient data" not a potentially spurious mean.
- Display a confidence interval (10th–90th percentile) alongside the seasonal average to communicate variability honestly.

**Detection:** Average price for tomato in April or May 2020 is anomalously low. When included in the 10-year seasonal calendar, April/May show artificially depressed "typical" prices — a farmer relying on this would underestimate the sell window value.

**Phase:** Seasonal calendar (Phase 1, first user-facing feature).

---

### Pitfall 12: LSTM Training on Short Commodity History — Overfitting at Scale

**What goes wrong:** LSTM is reserved for volatile commodities (onion, tomato, potato) which have sufficient data. However, LSTM overfitting is more dangerous than XGBoost overfitting because it is harder to detect: the training loss curve can look healthy while the model memorises year-specific noise (e.g., "in 2023 there was a specific spike" becomes a learned pattern, not a generalizable one).

For this project, daily price sequences of length 30 days means a commodity with 3 years of data = ~1,095 overlapping windows. This is adequate but not abundant. LSTM with 2+ layers and 128+ hidden units will overfit on this volume.

**Prevention:**
- Keep LSTM architecture small: 1 LSTM layer with 64 hidden units, 1 dense output layer. Add dropout (0.2) between LSTM and dense.
- Use early stopping on walk-forward validation loss, not training loss.
- Compare LSTM vs XGBoost on the same commodity-district pair using identical walk-forward folds. Only deploy LSTM for a pair if it beats XGBoost by > 5% RMSE — otherwise use the simpler model.
- Training should use sequence-to-one (predict next day only), not sequence-to-sequence (predict 30 days at once). Multi-step predictions should use recursive one-step-ahead (feed previous prediction as next input).

**Detection:** LSTM validation loss diverges from training loss after epoch 10–15. The gap between training RMSE and walk-forward RMSE exceeds 40%.

**Phase:** LSTM phase (Phase 5 or later). Do not begin LSTM until XGBoost baseline is validated.

---

## Minor Pitfalls

### Pitfall 13: Forecast Cache Staleness After Model Retraining

**What goes wrong:** The `forecast_cache` table stores precomputed forecasts. If a model is retrained (new data, corrected bug), the cache must be invalidated. Without explicit invalidation, the API serves stale predictions from the old model while claiming they are current.

**Prevention:**
- Include a `model_version` column and `trained_through_date` in the `forecast_cache` table. Every cache read must check that `model_version` matches the currently loaded model.
- Add a cache invalidation endpoint for admin use: `POST /admin/forecasts/invalidate?commodity=X&district=Y`.
- Set a maximum TTL on all cached forecasts: 7 days. After 7 days, the forecast is recomputed regardless of model version.

**Phase:** ML serving (Phase 6).

---

### Pitfall 14: Missing Rainfall Years Creating Silent Feature Gaps

**What goes wrong:** The rainfall dataset spans 1985–2026. However, for any district, there may be specific years with missing monthly records. If you compute "annual rainfall deficit" as a price feature and a year has 3 missing months, the annual figure is understated by 25–30% — appearing as a "severe drought year" even if those were simply unreported months.

**Prevention:**
- Before using rainfall features in any model, compute completeness per district per year: require at least 10 of 12 months present. If fewer, mark that year's annual features as NaN for that district.
- Use monthly rainfall features (lagged) rather than annual aggregations where possible — monthly data is more complete than annual rollups.

**Phase:** Rainfall feature engineering (part of Phase 3).

---

### Pitfall 15: Arbitage Dashboard Showing Stale Price Differentials

**What goes wrong:** The mandi arbitrage dashboard compares prices across mandis for the same commodity on the same day. If two mandis have different data freshness (one updated this week, one three weeks ago), the displayed differential is illusory. A farmer making a transport decision based on a stale differential wastes significant cost.

**Prevention:**
- Display `last_updated` date prominently on every mandi card in the arbitrage dashboard.
- Do not show price differentials unless both mandis have data within the past 7 days.
- Add a "Data freshness" warning icon for any mandi where `max(price_date) < today - 7 days`.

**Phase:** Arbitrage dashboard (frontend, Phase 7).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| District harmonisation (Phase 1) | Cascade errors from global fuzzy match | State-scoped matching, three-tier confidence, manual review of gray-zone matches |
| Seasonal calendar (Phase 1) | COVID/spike years distorting 10yr averages | Use median; compute pre/post-2020 separately; flag high-variability months |
| XGBoost baseline (Phase 2) | Random train/test split, not walk-forward | Implement `TimeSeriesSplit` before first hyperparameter tuning run |
| XGBoost baseline (Phase 2) | Training all 19k pairs including sparse ones | Apply 730-day minimum threshold; route sparse pairs to seasonal fallback |
| Feature engineering (Phase 3) | Rainfall look-ahead, rolling stats computed globally | Enforce `cutoff_date` parameter in all feature functions; never compute rolling stats before split |
| Feature engineering (Phase 3) | Missing mandi days treated as adjacent | Create complete daily grid first; use `days_since_last_observation` as explicit feature |
| Weather features (Phase 4) | Mean-imputing weather for 55% uncovered districts | Two-tier model, never impute; surface coverage tier in UI |
| Crop recommendation (Phase 5) | Block-average soil displayed as field-level | Always show distribution (% High/Medium/Low), never single label |
| LSTM training (Phase 5) | Overfitting on short sequences | Constrain architecture; compare to XGBoost baseline; only deploy if beats baseline by >5% |
| ML serving (Phase 6) | Memory multiplication with multiple workers | LRU cache with memory limit; model registry; lazy loading |
| ML serving (Phase 6) | Stale forecasts after model retrain | `model_version` in cache key; admin invalidation endpoint; 7-day TTL |
| Arbitrage dashboard (Phase 7) | Stale price differentials | Show `last_updated`; suppress differentials if either mandi is > 7 days stale |
| All phases | Price unit corruption from extreme values | Winsorise per commodity before any feature use; cap at `median × 20`; audit log all caps |

---

## Sources

**Empirical (this project's actual data):**
- Direct inspection of `agmarknet_daily_10yr.parquet` — CV% analysis confirming unit corruption
- Direct inspection of `nutrients_all.parquet` — confirmed percentage distribution schema (high+medium+low = 100)
- Gap analysis: 12,320 of 19,679 commodity-district pairs have at least one 90-day data gap

**Data leakage in time series:**
- [Data Leakage, Lookahead Bias, and Causality in Time Series Analytics](https://medium.com/@kyle-t-jones/data-leakage-lookahead-bias-and-causality-in-time-series-analytics-76e271ba2f6b) — MEDIUM confidence (WebSearch)
- [Examining Challenges in Implied Volatility Forecasting — Data Leakage](https://link.springer.com/article/10.1007/s10614-025-11172-z) — MEDIUM confidence (peer reviewed 2025)
- [How to Avoid ML Pitfalls — Academic Guide (arXiv)](https://arxiv.org/html/2108.02497v5) — MEDIUM confidence

**Walk-forward validation:**
- [Forecasting: Principles and Practice — Time Series Cross-Validation (official textbook)](https://otexts.com/fpp3/tscv.html) — HIGH confidence (authoritative academic source)
- [Backtesting ML Models for Time Series — MachineLearningMastery](https://machinelearningmastery.com/backtest-machine-learning-models-time-series-forecasting/) — MEDIUM confidence

**Agricultural structural breaks (India):**
- [COVID-19 Effects on Food Prices in India — European Review of Agricultural Economics (Oxford Academic)](https://academic.oup.com/erae/article/50/2/232/6643211) — HIGH confidence (peer reviewed)
- [Asymmetric Price Volatility of Onion in India — ISAE](https://isaeindia.org/wp-content/uploads/2021/07/03-Ranjit-Kumar-Paul.pdf) — MEDIUM confidence
- [Cash and the Economy: Evidence from India's Demonetization — QJE (Oxford Academic)](https://academic.oup.com/qje/article-abstract/135/1/57/5567189) — HIGH confidence (peer reviewed)

**District name harmonisation:**
- [Masala-Merge: Fuzzy Matching for Indian Location Names (GitHub)](https://github.com/paulnov/masala-merge) — MEDIUM confidence
- [IDInsight: Combining Datasets When Unique Identifiers Are Missing](https://www.idinsight.org/article/part-2-whats-in-a-name-combining-datasets-when-unique-identifiers-are-missing/) — MEDIUM confidence (empirical study, 47.5% vs 93.1% accuracy comparison)

**FastAPI model serving:**
- [FastAPI Discussion #7069 — Multiple Workers RAM Multiplication](https://github.com/fastapi/fastapi/discussions/7069) — HIGH confidence (official GitHub)
- [Chasing a Memory Leak in Async FastAPI Service — BetterUp Engineering](https://build.betterup.com/chasing-a-memory-leak-in-our-async-fastapi-service-how-jemalloc-fixed-our-rss-creep/) — MEDIUM confidence

**Soil health limitations:**
- [Soil Health Card Scheme Lessons — ResearchGate](https://www.researchgate.net/publication/347964502_The_Soil_Health_Card_Scheme_in_India_Lessons_Learned_and_Challenges_for_Replication_in_Other_Developing_Countries) — MEDIUM confidence
- [Official SHC Manual — NITI for States](https://www.nitiforstates.gov.in/public-assets/Policy/policy-repo/agriculture-and-allied-services/SNC511A000049.pdf) — HIGH confidence (government document)
