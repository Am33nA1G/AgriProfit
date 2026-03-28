# Database Missing Data Report

Snapshot date: 2026-03-11
Status: after Agmarknet backfill

## What Was Filled

- Backfilled missing commodity price history from the Agmarknet parquet snapshot.
- `price_history` grew from 27,023,230 rows to 32,897,672 rows.
- Commodity coverage improved from 388/466 to 466/466.
- Reusable backfill script added at `backend/scripts/backfill_missing_agmarknet_prices.py`.
- ETL batching was hardened to avoid PostgreSQL parameter-limit failures.

## Remaining Missing Data

### Missing Dates In `price_history`

- 2026-02-24
- 2026-02-27
- 2026-03-04

These dates are still absent from both the database and the local Agmarknet parquet snapshot.

### Mandis With No Price History

- Arkonam APMC, Vellore, Tamil Nadu
- Vanapuram APMC, Thiruvannamalai, Tamil Nadu
- Pochampalli APMC, Krishnagiri, Tamil Nadu
- Kudavasal APMC, Thiruvarur, Tamil Nadu
- Rajsamand, Rajasamand, Rajasthan
- Coimbatore, Coimbatore, Tamil Nadu
- Alangudi APMC, Pudukkottai, Tamil Nadu
- Manamadurai APMC, Sivaganga, Tamil Nadu
- Pali, Pali, Rajasthan
- Denkanikottai APMC, Krishnagiri, Tamil Nadu
- Pudukottai APMC, Pudukkottai, Tamil Nadu
- Acharapakkam APMC, Kancheepuram, Tamil Nadu
- Bhuvanagiri APMC, Cuddalore, Tamil Nadu
- Tittakudi APMC, Cuddalore, Tamil Nadu
- Dharampuri APMC, Dharmapuri, Tamil Nadu
- Thalavadi APMC, Erode, Tamil Nadu
- Kurinchipadi APMC, Cuddalore, Tamil Nadu
- Arur APMC, Dharmapuri, Tamil Nadu
- Chidambaram APMC, Cuddalore, Tamil Nadu
- Thimiri APMC, Vellore, Tamil Nadu
- Pennagaram APMC, Dharmapuri, Tamil Nadu
- Sathyamangalam APMC, Erode, Tamil Nadu
- Thiruvannamalai APMC, Thiruvannamalai, Tamil Nadu
- Elumathur APMC, Erode, Tamil Nadu

### Empty Or Missing Datasets

- `crop_yields`: 0 rows

### Missing Commodity Metadata

Total commodities: 466

- `description`: 466 null (100.0%)
- `growing_months`: 466 null (100.0%)
- `harvest_months`: 466 null (100.0%)
- `peak_season_start`: 466 null (100.0%)
- `peak_season_end`: 466 null (100.0%)
- `major_producing_states`: 466 null (100.0%)
- `name_local`: 175 null (37.6%)
- `category`: 165 null (35.4%)
- `unit`: 165 null (35.4%)

### Missing Mandi Metadata

Total mandis: 6,268

- `latitude`: 1,470 null (23.5%)
- `longitude`: 1,470 null (23.5%)
- Missing both coordinates: 1,470 mandis
- `pincode`: 6,268 null (100.0%)
- `phone`: 6,268 null (100.0%)
- `email`: 6,268 null (100.0%)
- `website`: 6,268 null (100.0%)
- `opening_time`: 6,268 null (100.0%)
- `closing_time`: 6,268 null (100.0%)
- `operating_days`: 6,268 null (100.0%)
- `payment_methods`: 6,268 null (100.0%)
- `commodities_accepted`: 6,268 null (100.0%)
- `rating`: 50 null (0.8%)

### Invalid `price_history` Values

- Invalid `modal_price` (`<= 0` or `> 1,000,000`): 258 rows
- Latest available price data in DB: 2026-03-06

## Important Limitation

The Agmarknet source used here is district-level in this repo's existing pipeline.
It is enough to backfill missing commodity history, but it does not expose named
APMC-level market rows in the shape needed to fill the remaining 24 mandi gaps
directly.

## Files To Check

- `backend/scripts/backfill_missing_agmarknet_prices.py`
- `backend/scripts/etl_parquet_to_postgres.py`
- `backend/database_gaps_report.json`
- `backend/logs/etl_20260311_003349.log`
