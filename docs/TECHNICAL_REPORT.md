# AgriProfit: A Machine Learning Platform for Agricultural Commodity Price Forecasting in Indian Markets

---

## Abstract

AgriProfit is a full-stack, production-grade agricultural market intelligence platform targeting Indian farmers, with an initial deployment focus on Kerala and pan-India coverage. The platform integrates ten years of daily modal wholesale price data sourced from Agmarknet APMCs (2015–2025), multi-source weather and soil datasets, and a tiered cascade of machine learning models to deliver 7-day ahead price forecasts, directional advisories, and yield predictions across 63 commodities spanning 458 districts. The primary production model — a direct multi-step XGBoost ensemble (v5) trained on 20 log-space features — achieves a median h7 MAPE of 12.9% across all commodities, with staple grains and oilseeds reaching under 5% MAPE. A 3-class direction classifier supplements the forecast with probabilistic up/flat/down signals. The platform serves 111+ REST API endpoints, processes 25 million price records, and delivers average API response times of 38 ms.

---

## 1. Dataset

### 1.1 Primary Price Dataset

The core training corpus is derived from **`agmarknet_daily_10yr.parquet`**, containing daily modal wholesale prices sourced from Agmarknet APMC records.

| Statistic | Value |
|---|---|
| Total rows | 25,132,794 |
| Total unique commodities | 314 |
| Active commodities (v5 threshold) | 63 |
| Date range | 2015 – 2025 (10 years) |
| Price unit | Indian Rupees per quintal (Rs/q), modal price |
| Geographic coverage | 458 districts across 26 Indian states |

**Preprocessing pipeline (v5)**:

1. Column-projected Parquet load via PyArrow to minimise memory footprint.
2. Rows with `price_modal ≤ 0` discarded.
3. Per-commodity outlier clipping to the \[p1, p99\] percentile range.
4. Known data-quality override: Arhar Dal uses `start_year = 2017` to exclude erroneous pre-2017 entries.
5. Mandi-to-district aggregation using the **median** modal price per district-day, making the signal robust to individual high-variability mandis.
6. Strict chronological train/test split: **train 2015–2023**, **test 2024–2025** (no shuffling, no future leakage).
7. Internal validation split: the final 180 days of the training window are held out for early stopping.
8. All prices log1p-transformed before feature construction; predictions are inverse-transformed (expm1) at serving time.

**Commodity qualification threshold (v5)**: ≥ 100,000 training rows **and** ≥ 80 districts. Sixty-three commodities met this bar.

Table 1 shows the ten largest commodities by training volume:

**Table 1 — Top 10 commodities by training rows**

| Commodity | Training rows | Districts |
|---|---|---|
| Potato | 716,588 | 454 |
| Onion | 698,396 | 458 |
| Tomato | 681,565 | 438 |
| Brinjal | 611,053 | 401 |
| Green Chilli | 546,583 | 391 |
| Wheat | 537,488 | 320 |
| Cauliflower | 455,138 | 376 |
| Cabbage | 439,185 | 389 |
| Bhindi (Ladies Finger) | 419,616 | 377 |
| Cucumber | 395,205 | 340 |

### 1.2 Secondary Datasets

| Dataset | Location | Coverage |
|---|---|---|
| IMD district-level monthly rainfall | `data/ranifall_data/combined/rainfall_district_monthly.parquet` | 616 districts, 1985–2026 |
| Weather monthly features (temp, humidity) | `data/features/weather_monthly_features.parquet` | 2021–2025, per-district |
| ICAR Soil Health Card (NP K/pH) | `data/soil-health/*.csv` | Block-level, pan-India |
| Crop yield | `data/crop_yields/yield_data_clean.parquet` | Crop × district × year |

---

## 2. Feature Engineering

### 2.1 V5 Features (7-Day Production Model)

The v5 model operates on **20 features** per row, all constructed after log1p-transforming `price_modal`. Rolling statistics are computed on a one-day lag (`shift(1)`) of the log-price series to eliminate same-day information leakage. The minimum series length required is 37 rows (30-day rolling window + 7 target days).

**Table 2 — V5 feature set (20 features)**

| Category | Features | Count |
|---|---|---|
| Price lags | lag_1, lag_2, lag_3, lag_7, lag_14, lag_21, lag_30 | 7 |
| Rolling mean | roll_mean_7, roll_mean_14, roll_mean_30 | 3 |
| Rolling std | roll_std_7, roll_std_14, roll_std_30 | 3 |
| Calendar | day_of_week, month, day_of_year, week_of_year | 4 |
| Categorical | district_enc (label-encoded integer) | 1 |
| Leakage guard | all rolling stats on shift(1) series | — |
| **Total** | | **20** |

**Targets**: Seven separate regression targets — `target_h1` … `target_h7` — each representing the log1p-transformed price *d* days ahead.

### 2.2 V4 Ensemble Features (30-Day Legacy Horizon)

The legacy v4 model uses commodity-category-specific lag sets plus a rich set of exogenous regressors totalling approximately 19 features per row.

**Table 3 — V4 lag sets by category**

| Category | Lags (days) |
|---|---|
| Vegetables | 1, 3, 7, 14, 30, 91 |
| Food grains | 7, 14, 30, 91, 182, 365 |
| Pulses | 7, 14, 30, 91, 182, 365 |
| Oilseeds | 7, 14, 30, 91, 182, 365 |
| Spices | 7, 14, 30, 91 |
| Fruits | 7, 14, 30, 91, 182, 365 |

**Table 4 — V4 exogenous features (~19)**

| Group | Features | Count |
|---|---|---|
| Fourier (deterministic seasonality) | sin/cos annual, sin/cos semi-annual, sin/cos weekly, sin/cos monthly | 8 |
| National price lags | price_lag_7d, 14d, 30d, 90d | 4 |
| National price rolling | roll_mean_7d, roll_mean_30d, roll_std_7d, roll_std_30d | 4 |
| Weather (Tier A+ districts) | avg_temp_c, avg_humidity, rainfall_mm | 3 |
| **Total** | | **~19** |

Prophet regressors mirror the Fourier set plus up to 3 weather variables and two domain-specific custom seasonalities: **Monsoon** (period = 121.75 days) and **Crop Cycle** (period = 182.6 days).

### 2.3 Direction Model Features (3-Class Advisory)

The direction advisory classifier uses **22+ features** per row.

| Category | Features |
|---|---|
| Lag returns | lag_1, lag_3, lag_7, lag_14, lag_30 + return at each lag (×2 = 10) |
| Rolling statistics | rolling_mean_7/14/30, rolling_std_7/14/30 (6) |
| Gap to mean | gap_to_mean_7/14/30 (3) |
| Volatility | volatility_7/14/30 (3) |
| Fourier | sin/cos annual, sin/cos weekly |
| Positional | history_index |

### 2.4 Yield Model Features (11 Features)

| Feature | Source |
|---|---|
| crop_encoded, district_encoded | Label encoding |
| yield_5yr_avg | Rolling historical yield |
| N_kg_ha, P_kg_ha, K_kg_ha, pH | ICAR Soil Health Cards (KNN-imputed, k=5) |
| annual_rainfall_mm, annual_rainfall_deviation_pct | IMD rainfall |
| avg_temp_c, avg_humidity | Weather monthly features |

---

## 3. Models

### 3.1 V5 — Direct Multi-Step XGBoost (Primary Production Model)

The v5 system trains **seven independent XGBRegressor instances per commodity**, one for each forecast horizon h1 … h7. This direct multi-step approach avoids the recursive error accumulation that affects autoregressive models when predicting beyond one step. Sixty-three commodities qualify, yielding **441 models** in total. Artifacts are serialised with joblib to `ml/artifacts/v5/{slug}_lgbm_7d.joblib`.

**Table 5 — V5 XGBoost hyperparameters (uniform across all commodities)**

| Parameter | Value |
|---|---|
| n_estimators | 400 |
| learning_rate | 0.05 |
| max_depth | 5 |
| min_child_weight | 20 |
| subsample | 0.8 |
| colsample_bytree | 0.8 |
| reg_alpha | 0.1 |
| reg_lambda | 1.0 |
| tree_method | hist |
| early_stopping_rounds | 30 |
| random_state | 42 |

**Prediction intervals**: Empirical 80% prediction bands are derived from the p10 and p90 quantiles of log-space residuals computed on the 2024–2025 holdout. At serving time: `log_low = log_pred + p10_residual`, `log_high = log_pred + p90_residual`, followed by expm1.

**Forecast confidence labels**: Green (h7 MAPE < 10%), Yellow (10–20%), Red (≥ 20%).

### 3.2 V4 — Prophet + XGBoost Ensemble (Legacy 30-Day Horizon)

The v4 ensemble covers ~250+ commodities with a longer 30-day forecast horizon. An inverse-MAPE weighted blend combines a per-commodity Prophet model with a multi-district XGBoost model trained using skforecast's `ForecasterRecursiveMultiSeries`. The blending weight α is constrained to \[0.1, 0.9\].

**Table 6 — V4 XGBoost hyperparameters by category**

| Category | n_estimators | max_depth | learning_rate | subsample |
|---|---|---|---|---|
| Vegetables | 600 | 8 | 0.02 | 0.7 |
| Food grains | 300 | 5 | 0.05 | 0.9 |
| Pulses | 400 | 6 | 0.03 | 0.8 |
| Oilseeds | 500 | 7 | 0.03 | 0.8 |
| Spices | 300 | 4 | 0.05 | 0.7 |
| Fruits | 400 | 6 | 0.03 | 0.8 |

**Table 7 — V4 Prophet hyperparameters by category**

| Category | changepoint_prior | seasonality_prior | n_changepoints | mode |
|---|---|---|---|---|
| Vegetables | 0.15 | 5 | 40 | multiplicative |
| Food grains | 0.03 | 15 | 20 | additive |
| Pulses | 0.05 | 10 | 25 | additive |
| Oilseeds | 0.07 | 10 | 30 | additive |
| Spices | 0.20 | 3 | 50 | multiplicative |
| Fruits | 0.10 | 8 | 30 | multiplicative |

**Commodity tiering (v4)**:

| Tier | Criterion | Model strategy | Target R² |
|---|---|---|---|
| A | ≥ 50 districts | Full ensemble (XGBoost + Prophet) | ≥ 0.80 |
| B | 10–49 districts | Full ensemble | ≥ 0.65 |
| C | < 10 districts | Prophet-only | ≥ 0.50 |
| D | < 730 days or R² < 0.30 | Seasonal average fallback | — |

### 3.3 Direction Advisory Classifier

A 3-class XGBClassifier predicts the 30-day price direction (down / flat / up) using walk-forward cross-validation with 4 splits and a 30-day test window per fold. The confidence threshold is chosen to guarantee a minimum 20% coverage on the validation set.

**Table 8 — Direction classifier hyperparameters**

| Parameter | Value |
|---|---|
| n_estimators | 300 |
| max_depth | 5 |
| learning_rate | 0.05 |
| subsample | 0.8 |
| colsample_bytree | 0.8 |
| min_child_weight | 3 |
| reg_alpha | 0.05 |
| reg_lambda | 1.0 |
| objective | multi:softprob |
| num_class | 3 |
| eval_metric | mlogloss |

### 3.4 Yield Prediction (Random Forest)

Crop yield is predicted by a set of RandomForestRegressors trained per agricultural category. Ten high-data-volume crops additionally receive individual per-crop models. Soil features are KNN-imputed (k=5, distance-weighted); weather features are forward-filled. Features are scaled with StandardScaler. The temporal test split uses the last three years of the dataset.

**Table 9 — Yield model hyperparameters**

| Scope | n_estimators | max_depth | min_samples_leaf |
|---|---|---|---|
| Category model | 200 | 10 | 3 |
| Per-crop model | 200 | 8 | 3 |

Category models trained: `food_grains`, `pulses`, `oilseeds`, `vegetables`, `fruits`, `cash_crops`. Individual models trained for Banana, Onion, and Potato.

---

## 4. Evaluation Metrics

Model quality is assessed using four metrics:

- **MAPE** (Mean Absolute Percentage Error) — relative forecast accuracy across price ranges.
- **R²** (coefficient of determination) — proportion of variance explained; primary gating metric for model deployment.
- **RMSE** (Root Mean Squared Error) — absolute error scale (used for yield models).
- **Accuracy / F1** — used for the 3-class direction classifier.

All v5 price metrics are computed on the **2024–2025 holdout set** in original price space after inverse-transforming (expm1) the log1p predictions.

---

## 5. Results

### 5.1 V5 7-Day XGBoost — Full Results

**Table 10 — V5 model performance on 2024–2025 holdout (all 61 reported commodities)**

| # | Commodity | h1 MAPE | h7 MAPE | h7 R² | Districts | Train rows |
|---|---|---|---|---|---|---|
| 1 | Potato | 7.5% | 10.1% | 0.778 | 454 | 716,588 |
| 2 | Onion | 9.4% | 13.4% | 0.397 | 458 | 698,396 |
| 3 | Tomato | 12.9% | 19.9% | 0.747 | 438 | 681,565 |
| 4 | Brinjal | 13.4% | 18.8% | 0.757 | 401 | 611,053 |
| 5 | Green Chilli | 12.0% | 16.7% | 0.817 | 391 | 546,583 |
| 6 | Wheat | 2.4% | 3.0% | 0.751 | 320 | 537,488 |
| 7 | Cauliflower | 15.7% | 23.4% | 0.635 | 376 | 455,138 |
| 8 | Cabbage | 13.3% | 18.3% | 0.803 | 389 | 439,185 |
| 9 | Bhindi (Ladies Finger) | 13.7% | 18.8% | 0.716 | 377 | 419,616 |
| 10 | Cucumber | 15.3% | 19.6% | 0.718 | 340 | 395,205 |
| 11 | Bottle Gourd | 15.3% | 19.8% | 0.658 | 302 | 366,248 |
| 12 | Bengal Gram | 3.0% | 4.1% | 0.798 | 269 | 389,299 |
| 13 | Bitter Gourd | 12.7% | 17.5% | 0.782 | 342 | 334,391 |
| 14 | Paddy (Common) | 4.1% | 4.9% | 0.751 | 324 | 377,501 |
| 15 | Banana | 7.7% | 9.0% | 0.855 | 281 | 344,709 |
| 16 | Pumpkin | 11.3% | 14.5% | 0.773 | 291 | 327,850 |
| 17 | Apple | 8.8% | 11.2% | 0.554 | 243 | 345,465 |
| 18 | Rice | 3.1% | 3.5% | 0.817 | 237 | 346,433 |
| 19 | Mustard | 2.4% | 3.4% | 0.790 | 221 | 328,852 |
| 20 | Ginger (Green) | 9.2% | 12.0% | 0.575 | 275 | 277,472 |
| 21 | Maize | 4.0% | 4.8% | 0.714 | 263 | 307,271 |
| 22 | Garlic | 14.6% | 18.2% | 0.291 | 265 | 267,793 |
| 23 | Carrot | 13.5% | 18.3% | 0.866 | 304 | 267,033 |
| 24 | Radish | 14.9% | 19.9% | 0.735 | 257 | 268,609 |
| 25 | Lemon | 11.0% | 15.2% | 0.714 | 237 | 234,308 |
| 26 | Pomegranate | 7.8% | 9.9% | 0.709 | 203 | 224,755 |
| 27 | Arhar (Tur / Red Gram) | 5.2% | 6.6% | 0.846 | 248 | 237,430 |
| 28 | Capsicum | 14.0% | 19.7% | 0.523 | 232 | 193,428 |
| 29 | Gur (Jaggery) | 2.4% | 3.1% | 0.614 | 147 | 224,522 |
| 30 | Black Gram | 5.8% | 6.9% | 0.886 | 245 | 215,958 |
| 31 | Papaya | 10.9% | 15.7% | 0.697 | 217 | 171,258 |
| 32 | Mousambi (Sweet Lime) | 6.1% | 7.9% | 0.772 | 187 | 180,021 |
| 33 | Green Gram (Moong) | 5.3% | 6.5% | 0.802 | 234 | 201,397 |
| 34 | Soyabean | 3.0% | 4.0% | 0.805 | 119 | 183,557 |
| 35 | Banana-Green | 7.8% | 9.2% | 0.865 | 169 | 164,510 |
| 36 | Lentil (Masur) | 2.1% | 2.6% | 0.920 | 162 | 174,712 |
| 37 | Bajra | 3.7% | 4.5% | 0.665 | 135 | 171,522 |
| 38 | Ridge Gourd | 15.3% | 20.9% | 0.674 | 216 | 143,034 |
| 39 | Coriander (Leaves)* | 70.1% | 89.8% | 0.672 | 167 | 137,958 |
| 40 | Spinach* | 28.2% | 33.4% | 0.666 | 138 | 145,173 |
| 41 | Cotton | 2.9% | 4.1% | 0.396 | 139 | 145,667 |
| 42 | Groundnut | 5.5% | 6.9% | 0.744 | 170 | 127,530 |
| 43 | Jowar (Sorghum) | 8.0% | 9.1% | 0.749 | 121 | 133,047 |
| 44 | Mango | 15.4% | 21.9% | 0.625 | 238 | 108,374 |
| 45 | Peas Wet | 14.7% | 21.9% | 0.740 | 127 | 111,745 |
| 46 | Arhar Dal (Tur Dal)† | 8.4% | 13.9% | −0.271 | 111 | 106,604 |
| 47 | Grapes | 15.6% | 19.7% | 0.610 | 194 | 104,123 |
| 48 | Orange | 13.1% | 17.3% | 0.683 | 189 | 96,634 |
| 49 | Guar | 12.1% | 16.6% | 0.311 | 85 | 106,587 |
| 50 | Water Melon | 13.0% | 18.0% | 0.555 | 201 | 91,048 |
| 51 | Colacasia | 10.8% | 14.3% | 0.779 | 151 | 84,854 |
| 52 | Barley (Jau) | 2.6% | 3.5% | 0.633 | 102 | 102,257 |
| 53 | Guava | 14.0% | 19.6% | 0.582 | 172 | 81,449 |
| 54 | Beetroot | 13.9% | 19.5% | 0.806 | 116 | 80,337 |
| 55 | Pointed Gourd | 9.7% | 14.4% | 0.695 | 124 | 90,524 |
| 56 | Ginger (Dry) | 12.0% | 15.7% | 0.867 | 124 | 98,474 |
| 57 | Mustard Oil | 1.1% | 1.7% | 0.846 | 90 | 100,048 |
| 58 | Sesamum | 6.3% | 8.3% | 0.674 | 120 | 95,625 |
| 59 | Drumstick | 21.2% | 29.4% | 0.587 | 94 | 77,370 |
| 60 | Pineapple | 12.8% | 17.0% | 0.571 | 112 | 80,104 |
| 61 | Coconut* | ~47% | — | — | 82 | 79,504 |

\* Demoted to seasonal fallback in production serving (MAPE too high for reliable forecasts).  
† Negative R² at h7 indicates the model underperforms a naive mean predictor at this horizon; v4 fallback or seasonal average is preferred in practice.

### 5.2 V5 Summary Statistics

**Table 11 — V5 aggregate performance across 58 reliably served commodities (excluding \*/**

| Metric | Value |
|---|---|
| Median h1 MAPE | ~9.4% |
| Median h7 MAPE | ~12.9% |
| Best h7 MAPE | **1.7%** (Mustard Oil) |
| Worst reliable h7 MAPE | 29.4% (Drumstick) |
| Commodities with h7 MAPE < 5% | 8 (Mustard Oil, Lentil, Wheat, Gur, Rice, Barley, Bajra, Paddy) |
| Best h7 R² | **0.920** (Lentil / Masur) |
| Commodities with h7 R² ≥ 0.80 | 18 |
| Median h7 R² | ~0.714 |

**Table 12 — Top 8 commodities by h7 MAPE (best performers)**

| Commodity | h7 MAPE | h7 R² |
|---|---|---|
| Mustard Oil | 1.7% | 0.846 |
| Lentil (Masur) | 2.6% | 0.920 |
| Wheat | 3.0% | 0.751 |
| Gur (Jaggery) | 3.1% | 0.614 |
| Rice | 3.5% | 0.817 |
| Barley (Jau) | 3.5% | 0.633 |
| Bajra | 4.5% | 0.665 |
| Paddy (Common) | 4.9% | 0.751 |

**Table 13 — Top 5 commodities by h7 R² (best explained variance)**

| Commodity | h7 R² | h7 MAPE |
|---|---|---|
| Lentil (Masur) | 0.920 | 2.6% |
| Black Gram | 0.886 | 6.9% |
| Carrot | 0.866 | 18.3% |
| Banana-Green | 0.865 | 9.2% |
| Banana | 0.855 | 9.0% |

### 5.3 Observed Error Patterns

**Stable commodities** (regulated MSP, low supply shock): grains (Wheat, Rice, Paddy), pulses (Lentil, Black Gram, Bengal Gram), and processed commodities (Mustard Oil, Gur) — all achieve h7 MAPE ≤ 7% and R² ≥ 0.75.

**Volatile commodities** (perishable, weather-driven): leaf vegetables (Coriander Leaves, Spinach), fresh fruits (Mango, Grapes), and gourds show substantially higher MAPE (15–30%) owing to supply shocks that are not predictable from price history alone.

**Unit-mix anomaly**: Coconut prices in Agmarknet are inconsistently recorded as Rs/piece vs. Rs/quintal across mandis, causing an apparent ~47% MAPE. This is a data provenance issue, not a modelling failure. The commodity is demoted to seasonal fallback in production.

---

## 6. System Architecture

### 6.1 Platform Overview

**Table 14 — Platform statistics**

| Aspect | Value |
|---|---|
| API endpoints | 111+ |
| Database models | 16 |
| Price records in PostgreSQL | 25 million+ |
| Frontend pages | 18 |
| Automated tests | 598 (100% passing) |
| Frontend test coverage | 61.37% |
| Avg. API response time | 38 ms |
| ML models in production | 441 (v5) + ~250 (v4) + direction + yield |

### 6.2 ML Serving Cascade

Each forecast request traverses a five-level cascade:

```
Request: GET /api/v1/forecasts?commodity=Onion&district=Nashik
       │
       ▼
Level 1 — V5 7-Day XGBoost
  Condition: v5 model exists AND commodity not in unreliable_slugs
  Output: 7-point daily forecast + 80% empirical prediction band
  Latency: ~50 ms (LRU cache hit)
       │ (fallthrough if condition fails)
       ▼
Level 2 — V4 Prophet + XGBoost Ensemble
  Condition: v4 meta exists, R² ≥ 0.30, prophet_mape ≤ 5.0
  Output: 30-day ensemble forecast + MAPE-weighted confidence bands
       │
       ▼
Level 3 — Seasonal Average Baseline
  Condition: {slug}_seasonal.json exists
  Output: Monthly median ± p10/p90 bands from historical distribution
       │
       ▼
Level 4 — National Average
  Output: National median price from parquet, Red confidence label
       │
       ▼
Level 5 — HTTP 404
```

### 6.3 Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), PostgreSQL, Alembic |
| ML / Data | XGBoost, scikit-learn, Prophet, skforecast, pandas, PyArrow, NumPy |
| Scheduling | APScheduler — price sync every 6 hours from data.gov.in |
| Frontend | Next.js 15 (App Router), TypeScript, shadcn/ui, Tailwind CSS, Recharts |
| State | TanStack Query (server state), Zustand (client state) |
| Mobile | React Native (Expo) |
| Auth | OTP via SMS → JWT (passwordless) |

### 6.4 Key ML Design Decisions

1. **Direct multi-step forecasting (v5)**: Seven independent regressors, one per horizon day, eliminate the recursive error accumulation present in the v4 autoregressive approach.
2. **Log1p transformation**: Normalises the price distribution across commodities that trade at dramatically different price levels (e.g., spices at ₹50,000/q vs. leafy greens at ₹200/q), making a single feature scale tractable.
3. **Strict temporal data splits**: Train on 2015–2023, evaluate on 2024–2025 holdout. No shuffling or group-based splitting at the district level — future leakage is structurally impossible.
4. **Empirical prediction bands**: p10/p90 quantiles of holdout log-space residuals are stored per commodity. This calibration step requires no distributional assumption and adapts to heteroskedasticity across different commodity volatility profiles.
5. **Commodity tiering (v4)**: Rather than forcing an XGBoost fit on sparse-data commodities, the tiering system gracefully degrades from full ensemble → Prophet-only → seasonal fallback based on measured data density and out-of-sample R². This prevents overfit models from serving confidently wrong forecasts.
6. **LRU model cache**: Models are lazy-loaded on first request and retained in an LRU cache (maxsize = 20), keeping RAM usage bounded while maintaining sub-50 ms serving latency.
7. **Three explicit demotions**: Coriander Leaves (90% MAPE — hyper-perishable weekly price swings), Coconut (47% MAPE — unit-mix data provenance issue), and Spinach (33% MAPE — supply shocks dominate signal) are explicitly excluded from v5 serving and fall through to seasonal baselines.

---

## 7. Limitations and Future Work

- **Hyper-perishable vegetables** (Coriander Leaves, Spinach, Drumstick) show high MAPE primarily because intra-week supply shocks carry more predictive weight than historical price patterns. Incorporating real-time arrival data from APMC gates or satellite-derived crop health indices could improve these commodities.
- **Arhar Dal** exhibits negative h7 R², suggesting the 2017-truncated training period or regional price-support interventions break stationarity assumptions at longer horizons.
- **Rainfall features** are not included in the current v5 model (they featured in early prototypes). Reintroducing district-level rainfall deviation and drought/flood signals — as in the v4 path — may improve seasonal accuracy for weather-sensitive crops.
- **Prediction bands** are calibrated on a two-year holdout. Wider distribution shift (e.g., crop failures, policy shocks) may invalidate the empirical quantiles; Conformal Prediction or quantile regression forests would provide coverage guarantees.
- **Mobile app**: Yield and soil advisory features are partially implemented; a full offline-capable mobile experience remains in progress.
