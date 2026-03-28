"""
Backfill Missing Price Data (Oct 31, 2025 - Feb 9, 2026)

Fetches historical price data from data.gov.in's Agmarknet archive resource
and inserts into the PostgreSQL price_history table using bulk INSERT with
ON CONFLICT for efficient deduplication.

Uses resource 35985678-0d79-46b4-9ed6-6f13308a1d24 with filters[Arrival_Date]
(capitalized!) which provides proper per-day filtering (~18K records/day).

Usage:
    python scripts/backfill_prices.py
    python scripts/backfill_prices.py --start-date 2025-11-01 --end-date 2025-11-30
    python scripts/backfill_prices.py --dry-run
"""
import sys
import os
import time
import logging
import argparse
from datetime import datetime, date, timedelta
from uuid import uuid4
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models import Commodity, Mandi
from app.models.price_history import PriceHistory

# Setup logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "backfill.log", encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# Suppress httpx logging noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# API Configuration
API_KEY = "579b464db66ec23bdd000001d55108bb212f421a449b34595f56cb15"
HISTORICAL_RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
BASE_URL = f"https://api.data.gov.in/resource/{HISTORICAL_RESOURCE_ID}"

# Commodity category mapping
COMMODITY_CATEGORIES = {
    "Wheat": "Grains", "Rice": "Grains", "Paddy": "Grains",
    "Paddy(Dhan)": "Grains", "Paddy(Dhan)(Common)": "Grains",
    "Maize": "Grains", "Bajra": "Grains",
    "Bajra(Pearl Millet/Cumbu)": "Grains",
    "Jowar": "Grains", "Jowar(Sorghum)": "Grains", "Sorghum": "Grains",
    "Barley(Jau)": "Grains", "Barley": "Grains", "Ragi": "Grains",
    "Arhar (Tur/Red Gram)": "Pulses", "Arhar Dal": "Pulses",
    "Moong": "Pulses", "Moong Dal": "Pulses",
    "Green Gram (Moong)": "Pulses", "Green Gram(Moong)(Whole)": "Pulses",
    "Urad": "Pulses", "Urad Dal": "Pulses",
    "Black Gram (Urd Beans)": "Pulses",
    "Chana": "Pulses", "Gram Dal": "Pulses",
    "Bengal Gram(Gram)": "Pulses", "Bengal Gram(Gram)(Whole)": "Pulses",
    "Masoor": "Pulses", "Masoor Dal": "Pulses", "Lentil (Masur)": "Pulses",
    "Kulthi(Horse Gram)": "Pulses", "Peas(Dry)": "Pulses",
    "Groundnut": "Oilseeds", "Mustard": "Oilseeds",
    "Mustard Oil": "Oilseeds", "Soyabean": "Oilseeds",
    "Soybean": "Oilseeds", "Sunflower": "Oilseeds",
    "Sesamum(Sesame,Gingelly,Til)": "Oilseeds",
    "Castor Seed": "Oilseeds", "Copra": "Oilseeds",
    "Coconut": "Oilseeds", "Coconut Oil": "Oilseeds",
    "Linseed": "Oilseeds", "Niger Seed(Ramtil)": "Oilseeds",
    "Safflower": "Oilseeds",
    "Cotton": "Cash Crops", "Sugarcane": "Cash Crops",
    "Arecanut(Betelnut/Supari)": "Cash Crops",
    "Betelnuts": "Cash Crops", "Rubber": "Cash Crops",
    "Tobacco": "Cash Crops", "Coconut Seed": "Cash Crops",
    "Dry Coconut": "Cash Crops",
    "Tomato": "Vegetables", "Potato": "Vegetables", "Onion": "Vegetables",
    "Brinjal": "Vegetables", "Cabbage": "Vegetables",
    "Cauliflower": "Vegetables", "Cauliflower(Whole)": "Vegetables",
    "Carrot": "Vegetables", "Beans": "Vegetables",
    "Peas Wet": "Vegetables", "Green Peas": "Vegetables",
    "Lady Finger": "Vegetables", "Bhindi(Ladies Finger)": "Vegetables",
    "Bitter Gourd": "Vegetables", "Bitter gourd": "Vegetables",
    "Bottle Gourd": "Vegetables", "Bottle gourd": "Vegetables",
    "Pumpkin": "Vegetables", "Cucumber": "Vegetables",
    "Cucumber(Kheera)": "Vegetables",
    "Spinach": "Vegetables", "Green Chilli": "Vegetables",
    "Capsicum": "Vegetables", "Raddish": "Vegetables",
    "Drumstick": "Vegetables", "Methi": "Vegetables",
    "Coriander": "Vegetables", "Coriander(Leaves)": "Vegetables",
    "Amaranthus": "Vegetables", "Ash Gourd": "Vegetables",
    "Ashgourd": "Vegetables", "Cluster beans": "Vegetables",
    "Colacasia": "Vegetables", "Elephant Yam (Suran)": "Vegetables",
    "French Beans (Frasbean)": "Vegetables", "Guar": "Vegetables",
    "Ivy Gourd(Tendli)": "Vegetables", "Knool Khol": "Vegetables",
    "Long Melon(Kakri)": "Vegetables",
    "Pointed gourd (Parval)": "Vegetables",
    "Ridgeguard(Tori)": "Vegetables", "Round gourd": "Vegetables",
    "Seemebadnekai": "Vegetables", "Snake Gourd": "Vegetables",
    "Snakeguard": "Vegetables", "Sponge Gourd": "Vegetables",
    "Sweet Potato": "Vegetables", "Tapioca": "Vegetables",
    "Tinda": "Vegetables", "Turnip": "Vegetables",
    "White Pumpkin": "Vegetables",
    "Apple": "Fruits", "Banana": "Fruits", "Mango": "Fruits",
    "Mango (Raw-Loss)": "Fruits", "Grapes": "Fruits",
    "Orange": "Fruits", "Papaya": "Fruits", "Pomegranate": "Fruits",
    "Watermelon": "Fruits", "Guava": "Fruits", "Lemon": "Fruits",
    "Lime": "Fruits", "Mousambi(Sweet Lime)": "Fruits",
    "Pineapple": "Fruits", "Sapota": "Fruits", "Sweet melon": "Fruits",
    "Chillies": "Spices", "Dry Chillies": "Spices",
    "Red Chillies": "Spices", "Turmeric": "Spices",
    "Turmeric (Whole)": "Spices", "Turmeric(Bulb)": "Spices",
    "Ginger": "Spices", "Ginger(Dry)": "Spices",
    "Ginger(Green)": "Spices", "Garlic": "Spices",
    "Coriander Seed": "Spices", "Coriander seed": "Spices",
    "Cumin Seed": "Spices", "Cummin Seed(Jeera)": "Spices",
    "Fennel Seed": "Spices", "Fenugreek Seed": "Spices",
    "Black Pepper": "Spices", "Ajwan": "Spices",
    "Cardamom": "Spices", "Cloves": "Spices",
    "Tamarind Fruit": "Spices",
    "Sugar": "Sugar", "Jaggery": "Sugar", "Gur": "Sugar",
    "Gur(Jaggery)": "Sugar",
    "Tea": "Beverages", "Coffee": "Beverages",
}


class BackfillClient:
    """HTTP client for the historical Agmarknet resource."""

    def __init__(self):
        self.client = httpx.Client(timeout=180.0)
        self.request_count = 0
        self.total_bytes = 0
        self._last_429 = False

    def fetch_date(self, date_str: str, limit: int = 1000, offset: int = 0,
                   retries: int = 8) -> dict:
        """Fetch records for a specific date using filters[Arrival_Date]."""
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": limit,
            "offset": offset,
            "filters[Arrival_Date]": date_str,  # MUST be capitalized!
        }

        last_exception = None
        for attempt in range(retries + 1):
            try:
                if attempt > 0:
                    # Longer backoff for 429 errors
                    if self._last_429:
                        wait = min(60 * attempt, 300)  # 60s, 120s, 180s... up to 5min
                        logger.info(f"  Rate limited, waiting {wait}s...")
                    else:
                        wait = min(2 ** attempt, 60)
                    time.sleep(wait)

                resp = self.client.get(BASE_URL, params=params)
                self.request_count += 1
                self.total_bytes += len(resp.content)

                if resp.status_code == 429:
                    self._last_429 = True
                    raise httpx.HTTPStatusError(
                        f"429 Too Many Requests", request=resp.request, response=resp
                    )

                self._last_429 = False
                resp.raise_for_status()
                return resp.json()

            except (httpx.HTTPError, httpx.ReadTimeout) as e:
                last_exception = e
                if "429" in str(e):
                    self._last_429 = True
                logger.warning(f"  API error (attempt {attempt+1}): {type(e).__name__}")

        raise last_exception

    def fetch_all_for_date(self, date_str: str) -> list[dict]:
        """Fetch ALL records for a specific date using pagination."""
        all_records = []
        offset = 0
        batch_size = 1000

        data = self.fetch_date(date_str, limit=batch_size, offset=0)
        total = int(data.get("total", 0))
        records = data.get("records", [])
        all_records.extend(records)

        if total == 0:
            return []

        while len(all_records) < total:
            offset += batch_size
            time.sleep(2.0)  # 2s between pages to avoid 429

            data = self.fetch_date(date_str, limit=batch_size, offset=offset)
            records = data.get("records", [])
            if not records:
                break
            all_records.extend(records)

        return all_records

    def close(self):
        self.client.close()


class BackfillSeeder:
    """Seeds price data using bulk INSERT with ON CONFLICT for efficiency."""

    def __init__(self, db: Session):
        self.db = db
        self._commodity_cache: dict[str, str] = {}  # name -> id (str)
        self._mandi_cache: dict[str, str] = {}  # "name|district|state" -> id (str)
        self.stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "new_commodities": 0,
            "new_mandis": 0,
        }

    def load_caches(self):
        """Pre-load commodity and mandi caches from DB."""
        logger.info("Loading commodity and mandi caches...")

        result = self.db.execute(text("SELECT id, name FROM commodities"))
        for row in result:
            self._commodity_cache[row[1]] = str(row[0])
        logger.info(f"  Loaded {len(self._commodity_cache)} commodities")

        result = self.db.execute(text("SELECT id, name, district, state FROM mandis"))
        for row in result:
            key = f"{row[1]}|{row[2]}|{row[3]}"
            self._mandi_cache[key] = str(row[0])
        logger.info(f"  Loaded {len(self._mandi_cache)} mandis")

    def _ensure_commodity(self, name: str) -> str:
        """Get or create commodity, return ID."""
        if name in self._commodity_cache:
            return self._commodity_cache[name]

        # Check DB
        result = self.db.execute(
            text("SELECT id FROM commodities WHERE name = :name"),
            {"name": name}
        )
        row = result.fetchone()
        if row:
            self._commodity_cache[name] = str(row[0])
            return str(row[0])

        # Create new
        new_id = str(uuid4())
        category = COMMODITY_CATEGORIES.get(name, "Other")
        self.db.execute(text("""
            INSERT INTO commodities (id, name, name_local, category, unit, is_active, created_at, updated_at)
            VALUES (:id, :name, :name_local, :category, 'quintal', true, NOW(), NOW())
            ON CONFLICT (name) DO NOTHING
        """), {"id": new_id, "name": name, "name_local": name, "category": category})
        self.db.commit()

        # Re-fetch to get the actual ID (in case of race condition)
        result = self.db.execute(
            text("SELECT id FROM commodities WHERE name = :name"),
            {"name": name}
        )
        row = result.fetchone()
        actual_id = str(row[0])
        self._commodity_cache[name] = actual_id
        self.stats["new_commodities"] += 1
        logger.info(f"  + New commodity: {name} ({category})")
        return actual_id

    def _ensure_mandi(self, name: str, district: str, state: str) -> str:
        """Get or create mandi, return ID."""
        key = f"{name}|{district}|{state}"
        if key in self._mandi_cache:
            return self._mandi_cache[key]

        # Check DB
        result = self.db.execute(
            text("SELECT id FROM mandis WHERE name = :name AND district = :district AND state = :state"),
            {"name": name, "district": district, "state": state}
        )
        row = result.fetchone()
        if row:
            self._mandi_cache[key] = str(row[0])
            return str(row[0])

        # Create new
        new_id = str(uuid4())
        market_code = "".join(c for c in name.upper() if c.isalnum())[:10] + str(uuid4())[:4].upper()
        address = f"{name}, {district}, {state}"
        self.db.execute(text("""
            INSERT INTO mandis (id, name, market_code, state, district, address, is_active, created_at, updated_at)
            VALUES (:id, :name, :code, :state, :district, :address, true, NOW(), NOW())
        """), {"id": new_id, "name": name, "code": market_code,
               "state": state, "district": district, "address": address})
        self.db.commit()

        self._mandi_cache[key] = new_id
        self.stats["new_mandis"] += 1
        logger.info(f"  + New mandi: {name}, {district}, {state}")
        return new_id

    def seed_day(self, records: list[dict], target_date: date) -> int:
        """
        Seed records for a single day using bulk INSERT with ON CONFLICT.

        Returns number of new records created.
        """
        if not records:
            return 0

        # First pass: ensure all commodities and mandis exist
        seen_commodities = set()
        seen_mandis = set()
        for r in records:
            commodity = str(r.get("Commodity", "")).strip()
            market = str(r.get("Market", "")).strip()
            state = str(r.get("State", "")).strip()
            district = str(r.get("District", "")).strip()

            if commodity and commodity not in seen_commodities:
                seen_commodities.add(commodity)
                self._ensure_commodity(commodity)

            if market and district and state:
                mandi_key = f"{market}|{district}|{state}"
                if mandi_key not in seen_mandis:
                    seen_mandis.add(mandi_key)
                    self._ensure_mandi(market, district, state)

        # Second pass: build batch values for bulk insert
        values = []
        seen_keys = set()

        for r in records:
            commodity = str(r.get("Commodity", "")).strip()
            market = str(r.get("Market", "")).strip()
            state = str(r.get("State", "")).strip()
            district = str(r.get("District", "")).strip()
            date_str = str(r.get("Arrival_Date", "")).strip()

            if not commodity or not market or not date_str:
                self.stats["skipped"] += 1
                continue

            # Parse and verify date
            try:
                record_date = datetime.strptime(date_str, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                self.stats["skipped"] += 1
                continue

            # Only accept records matching our target date
            if record_date != target_date:
                self.stats["skipped"] += 1
                continue

            # Parse prices
            try:
                min_price = float(r.get("Min_Price", 0) or 0)
                max_price = float(r.get("Max_Price", 0) or 0)
                modal_price = float(r.get("Modal_Price", 0) or 0)
            except (ValueError, TypeError):
                self.stats["skipped"] += 1
                continue

            if modal_price <= 0:
                self.stats["skipped"] += 1
                continue

            # Clamp to numeric(10,2) max: 99999999.99
            MAX_PRICE = 99999999.99
            min_price = min(min_price, MAX_PRICE)
            max_price = min(max_price, MAX_PRICE)
            modal_price = min(modal_price, MAX_PRICE)

            # Get IDs
            commodity_id = self._commodity_cache.get(commodity)
            mandi_key = f"{market}|{district}|{state}"
            mandi_id = self._mandi_cache.get(mandi_key)

            if not commodity_id or not mandi_id:
                self.stats["skipped"] += 1
                continue

            # Deduplicate within batch
            dedup_key = (commodity_id, market, record_date.isoformat())
            if dedup_key in seen_keys:
                self.stats["skipped"] += 1
                continue
            seen_keys.add(dedup_key)

            values.append({
                "id": str(uuid4()),
                "commodity_id": commodity_id,
                "mandi_id": mandi_id,
                "mandi_name": market,
                "min_price": min_price,
                "max_price": max_price,
                "modal_price": modal_price,
                "price_date": record_date,
            })

        if not values:
            return 0

        # Bulk insert with ON CONFLICT
        created = 0
        batch_size = 500
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]

            # Build parameterized INSERT
            placeholders = []
            params = {}
            for j, v in enumerate(batch):
                prefix = f"v{j}_"
                placeholders.append(
                    f"(:{prefix}id, :{prefix}cid, :{prefix}mid, :{prefix}mn, "
                    f":{prefix}minp, :{prefix}maxp, :{prefix}modp, :{prefix}pd, NOW(), NOW())"
                )
                params[f"{prefix}id"] = v["id"]
                params[f"{prefix}cid"] = v["commodity_id"]
                params[f"{prefix}mid"] = v["mandi_id"]
                params[f"{prefix}mn"] = v["mandi_name"]
                params[f"{prefix}minp"] = v["min_price"]
                params[f"{prefix}maxp"] = v["max_price"]
                params[f"{prefix}modp"] = v["modal_price"]
                params[f"{prefix}pd"] = v["price_date"]

            sql = f"""
                INSERT INTO price_history
                    (id, commodity_id, mandi_id, mandi_name, min_price, max_price,
                     modal_price, price_date, created_at, updated_at)
                VALUES {', '.join(placeholders)}
                ON CONFLICT (commodity_id, mandi_name, price_date)
                DO UPDATE SET
                    min_price = EXCLUDED.min_price,
                    max_price = EXCLUDED.max_price,
                    modal_price = EXCLUDED.modal_price,
                    updated_at = NOW()
            """

            try:
                self.db.execute(text(sql), params)
                self.db.commit()
                created += len(batch)
            except Exception as e:
                self.db.rollback()
                logger.warning(f"  Batch insert error: {type(e).__name__}: {str(e)[:80]}")
                self.stats["skipped"] += len(batch)

        self.stats["created"] += created
        return created


def get_dates_with_data(db: Session, start: date, end: date) -> dict[date, int]:
    """Get count of existing records per date in range."""
    result = db.execute(text("""
        SELECT price_date, COUNT(*) as cnt
        FROM price_history
        WHERE price_date >= :start AND price_date <= :end
        GROUP BY price_date
        ORDER BY price_date
    """), {"start": start, "end": end})
    return {row[0]: row[1] for row in result}


def main():
    parser = argparse.ArgumentParser(description="Backfill missing price data")
    parser.add_argument("--start-date", default="2025-10-31",
                        help="Start date YYYY-MM-DD (default: 2025-10-31)")
    parser.add_argument("--end-date", default="2026-02-09",
                        help="End date YYYY-MM-DD (default: 2026-02-09)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only fetch and report, don't insert")
    parser.add_argument("--min-existing", type=int, default=5000,
                        help="Skip date if it already has this many records (default: 5000)")
    parser.add_argument("--force", action="store_true",
                        help="Process all dates even if data exists")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    total_days = (end_date - start_date).days + 1

    print("=" * 70)
    print("AGMARKNET PRICE DATA BACKFILL")
    print("=" * 70)
    print(f"Date range: {start_date} to {end_date} ({total_days} days)")
    print(f"Resource:   {HISTORICAL_RESOURCE_ID}")
    print(f"Filter:     filters[Arrival_Date] (capitalized, exact match)")
    print(f"Dry run:    {args.dry_run}")
    print(f"Skip if >= {args.min_existing} existing records (--force to override)")
    print("=" * 70)

    db = SessionLocal()
    client = BackfillClient()

    try:
        # Check existing data coverage
        logger.info("Checking existing data coverage...")
        existing_data = get_dates_with_data(db, start_date, end_date)
        if not args.force:
            dates_to_skip = {d for d, cnt in existing_data.items() if cnt >= args.min_existing}
        else:
            dates_to_skip = set()
        logger.info(f"  {len(dates_to_skip)} dates already have sufficient data")

        # Initialize seeder
        seeder = BackfillSeeder(db)
        seeder.load_caches()

        # Process each date
        overall_start = time.time()
        days_processed = 0
        days_skipped = 0
        total_fetched = 0
        total_inserted = 0
        errors = []

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%d/%m/%Y")
            day_num = (current_date - start_date).days + 1

            # Skip if already has data
            if current_date in dates_to_skip:
                days_skipped += 1
                existing_cnt = existing_data.get(current_date, 0)
                logger.info(f"[{day_num}/{total_days}] {current_date} - SKIP ({existing_cnt:,} records)")
                current_date += timedelta(days=1)
                continue

            logger.info(f"[{day_num}/{total_days}] {current_date} - Fetching...")

            try:
                records = client.fetch_all_for_date(date_str)
                total_fetched += len(records)

                if not records:
                    logger.info(f"  No records for {current_date}")
                    current_date += timedelta(days=1)
                    days_processed += 1
                    continue

                logger.info(f"  Fetched {len(records):,} records from API")

                if not args.dry_run:
                    created = seeder.seed_day(records, current_date)
                    total_inserted += created
                    logger.info(
                        f"  Inserted/updated {created:,} records "
                        f"(running total: {total_inserted:,})"
                    )
                else:
                    logger.info(f"  [DRY RUN] Would process ~{len(records):,} records")

                days_processed += 1

            except Exception as e:
                error_msg = f"{current_date}: {type(e).__name__}: {str(e)[:100]}"
                errors.append(error_msg)
                logger.error(f"  ERROR: {error_msg}")
                days_processed += 1

            # Rate limiting - generous delay to avoid 429
            time.sleep(5.0)
            current_date += timedelta(days=1)

            # Progress every 10 days
            if days_processed % 10 == 0 and days_processed > 0:
                elapsed = time.time() - overall_start
                rate = days_processed / (elapsed / 60) if elapsed > 0 else 0
                remaining_days = total_days - days_processed - days_skipped
                eta = remaining_days / rate if rate > 0 else 0
                logger.info(
                    f"  --- PROGRESS: {days_processed + days_skipped}/{total_days} days | "
                    f"{total_fetched:,} fetched | {total_inserted:,} inserted | "
                    f"Rate: {rate:.1f} days/min | ETA: {eta:.0f} min ---"
                )

        # Summary
        elapsed = time.time() - overall_start
        print("\n" + "=" * 70)
        print("BACKFILL COMPLETE")
        print("=" * 70)
        print(f"Duration:       {elapsed / 60:.1f} minutes")
        print(f"Days processed: {days_processed}")
        print(f"Days skipped:   {days_skipped}")
        print(f"API records:    {total_fetched:,}")
        print(f"API requests:   {client.request_count}")
        print(f"Data transfer:  {client.total_bytes / 1024 / 1024:.1f} MB")

        if not args.dry_run:
            print(f"\nDatabase changes:")
            print(f"  Records inserted/updated: {seeder.stats['created']:,}")
            print(f"  Records skipped:          {seeder.stats['skipped']:,}")
            print(f"  New commodities:          {seeder.stats['new_commodities']}")
            print(f"  New mandis:               {seeder.stats['new_mandis']}")

        if errors:
            print(f"\nErrors ({len(errors)}):")
            for err in errors:
                print(f"  {err}")

        print("=" * 70)
        return 0 if not errors else 1

    finally:
        client.close()
        db.close()


if __name__ == "__main__":
    sys.exit(main())
