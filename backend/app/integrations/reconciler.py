"""
Data reconciliation service.

Coordinates gap detection and backfill from the historical Agmarknet
fallback source.  Designed to run safely alongside the existing
6-hourly sync pipeline (never replaces it).

Usage (scheduled):
    Called by APScheduler daily – see scheduler.py

Usage (manual):
    python scripts/reconcile_data.py --last-7-days --dry-run
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.gap_detector import GapDetector, DataGap, GapSummary
from app.integrations.ashoka_client import FallbackDataClient

logger = logging.getLogger(__name__)

# Commodity category mapping (subset – reuse from seeder for new entries)
_COMMODITY_CATEGORIES = {
    "Wheat": "Grains", "Rice": "Grains", "Paddy": "Grains",
    "Paddy(Dhan)": "Grains", "Paddy(Dhan)(Common)": "Grains",
    "Maize": "Grains", "Bajra": "Grains", "Jowar": "Grains",
    "Barley": "Grains", "Barley(Jau)": "Grains", "Ragi": "Grains",
    "Tomato": "Vegetables", "Potato": "Vegetables", "Onion": "Vegetables",
    "Brinjal": "Vegetables", "Cabbage": "Vegetables",
    "Cauliflower": "Vegetables", "Carrot": "Vegetables",
    "Groundnut": "Oilseeds", "Mustard": "Oilseeds", "Soyabean": "Oilseeds",
    "Cotton": "Cash Crops", "Sugarcane": "Cash Crops",
    "Arhar (Tur/Red Gram)": "Pulses", "Moong": "Pulses",
    "Urad": "Pulses", "Chana": "Pulses", "Masoor": "Pulses",
    "Apple": "Fruits", "Banana": "Fruits", "Mango": "Fruits",
    "Chillies": "Spices", "Turmeric": "Spices", "Ginger": "Spices",
    "Garlic": "Spices",
    "Sugar": "Sugar", "Jaggery": "Sugar",
}


@dataclass
class ReconciliationStats:
    """Statistics for a single reconciliation run."""

    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    gaps_detected: int = 0
    gaps_attempted: int = 0
    gaps_filled: int = 0
    records_fetched: int = 0
    records_upserted: int = 0
    records_skipped: int = 0
    new_commodities: int = 0
    new_mandis: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False

    def __str__(self) -> str:
        status = "DRY RUN" if self.dry_run else "LIVE"
        return (
            f"Reconciliation [{status}]: "
            f"{self.gaps_detected} gaps detected, "
            f"{self.gaps_filled}/{self.gaps_attempted} filled, "
            f"{self.records_upserted} records upserted, "
            f"{len(self.errors)} errors"
        )


class DataReconciler:
    """
    Detects gaps in price_history and fills them from the historical
    Agmarknet resource on data.gov.in.

    Uses bulk INSERT … ON CONFLICT (same pattern as backfill_prices.py)
    to safely upsert without creating duplicates.
    """

    # Don't bother trying to fill a date that already has enough data
    SKIP_THRESHOLD = 5000

    def __init__(self, db: Session):
        self.db = db
        self.detector = GapDetector(db)
        self._commodity_cache: dict[str, str] = {}  # name -> id
        self._mandi_cache: dict[str, str] = {}       # "name|district|state" -> id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reconcile(
        self,
        start_date: date,
        end_date: date,
        dry_run: bool = False,
        sparse_threshold: int = GapDetector.DEFAULT_SPARSE_THRESHOLD,
    ) -> ReconciliationStats:
        """
        Run a full reconciliation cycle.

        1. Detect date-level gaps (complete + sparse).
        2. For each gap, fetch records from fallback source.
        3. Upsert into price_history.

        Args:
            start_date: Start of reconciliation window.
            end_date: End of reconciliation window.
            dry_run: If True, detect gaps but don't fetch/insert.
            sparse_threshold: Records/day below which a day is "sparse".

        Returns:
            ReconciliationStats.
        """
        stats = ReconciliationStats(dry_run=dry_run)
        logger.info(
            "Starting reconciliation: %s to %s (dry_run=%s)",
            start_date, end_date, dry_run,
        )

        # Step 1: detect gaps
        summary = self.detector.detect_gaps(start_date, end_date, sparse_threshold)
        actionable = summary.actionable_gaps
        stats.gaps_detected = summary.gap_count

        if not actionable:
            logger.info("No actionable gaps found – database looks complete.")
            stats.finished_at = datetime.now()
            return stats

        self._log_gap_summary(summary)

        if dry_run:
            logger.info("Dry run – skipping fetch & insert.")
            stats.finished_at = datetime.now()
            return stats

        # Step 2: load caches for fast commodity/mandi lookups
        self._load_caches()

        # Step 3: fill each gap
        try:
            client = FallbackDataClient()
        except ValueError as exc:
            logger.error("Cannot create fallback client: %s", exc)
            stats.errors.append(str(exc))
            stats.finished_at = datetime.now()
            return stats

        try:
            for gap in actionable:
                stats.gaps_attempted += 1
                try:
                    self._fill_gap(gap, client, stats)
                except Exception as exc:
                    msg = f"Error filling gap {gap.gap_date}: {exc}"
                    logger.error(msg, exc_info=True)
                    stats.errors.append(msg)
                # Rate limit between dates
                time.sleep(FallbackDataClient.REQUEST_DELAY)
        finally:
            client.close()

        stats.finished_at = datetime.now()
        logger.info("Reconciliation finished: %s", stats)
        return stats

    # ------------------------------------------------------------------
    # Gap filling
    # ------------------------------------------------------------------

    def _fill_gap(
        self,
        gap: DataGap,
        client: FallbackDataClient,
        stats: ReconciliationStats,
    ) -> None:
        """Fetch records for a single gap date and upsert."""
        target = gap.gap_date
        logger.info("Filling gap: %s (%s)", target, gap.details)

        records = client.fetch_date(target)
        stats.records_fetched += len(records)

        if not records:
            logger.warning("  No data from fallback source for %s", target)
            return

        upserted = self._upsert_records(records, target, stats)
        if upserted > 0:
            stats.gaps_filled += 1
            logger.info("  Filled %s: %d records upserted", target, upserted)
        else:
            logger.info("  %s: 0 new records (all already existed)", target)

    def _upsert_records(
        self,
        records: list[dict],
        target_date: date,
        stats: ReconciliationStats,
    ) -> int:
        """
        Upsert raw API records into price_history using bulk INSERT
        with ON CONFLICT.  Returns count of rows upserted.
        """
        # First pass: ensure all commodities and mandis exist
        seen_commodities: set[str] = set()
        seen_mandis: set[str] = set()

        for r in records:
            commodity = str(r.get("Commodity") or r.get("commodity", "")).strip()
            market = str(r.get("Market") or r.get("market", "")).strip()
            state = str(r.get("State") or r.get("state", "")).strip()
            district = str(r.get("District") or r.get("district", "")).strip()

            if commodity and commodity not in seen_commodities:
                seen_commodities.add(commodity)
                self._ensure_commodity(commodity, stats)

            if market and district and state:
                mkey = f"{market}|{district}|{state}"
                if mkey not in seen_mandis:
                    seen_mandis.add(mkey)
                    self._ensure_mandi(market, district, state, stats)

        # Second pass: build values for bulk insert
        values: list[dict] = []
        seen_keys: set[tuple] = set()

        for r in records:
            commodity = str(r.get("Commodity") or r.get("commodity", "")).strip()
            market = str(r.get("Market") or r.get("market", "")).strip()
            state = str(r.get("State") or r.get("state", "")).strip()
            district = str(r.get("District") or r.get("district", "")).strip()
            date_str = str(
                r.get("Arrival_Date") or r.get("arrival_date", "")
            ).strip()

            if not commodity or not market or not date_str:
                stats.records_skipped += 1
                continue

            # Parse date
            try:
                from datetime import datetime as dt

                record_date = dt.strptime(date_str, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                stats.records_skipped += 1
                continue

            if record_date != target_date:
                stats.records_skipped += 1
                continue

            # Parse prices
            try:
                min_price = float(r.get("Min_Price") or r.get("min_price", 0) or 0)
                max_price = float(r.get("Max_Price") or r.get("max_price", 0) or 0)
                modal_price = float(
                    r.get("Modal_Price") or r.get("modal_price", 0) or 0
                )
            except (ValueError, TypeError):
                stats.records_skipped += 1
                continue

            if modal_price <= 0:
                stats.records_skipped += 1
                continue

            # Clamp to numeric(10,2) max
            MAX_PRICE = 99_999_999.99
            min_price = min(min_price, MAX_PRICE)
            max_price = min(max_price, MAX_PRICE)
            modal_price = min(modal_price, MAX_PRICE)

            commodity_id = self._commodity_cache.get(commodity)
            mandi_key = f"{market}|{district}|{state}"
            mandi_id = self._mandi_cache.get(mandi_key)

            if not commodity_id or not mandi_id:
                stats.records_skipped += 1
                continue

            dedup_key = (commodity_id, market, record_date.isoformat())
            if dedup_key in seen_keys:
                stats.records_skipped += 1
                continue
            seen_keys.add(dedup_key)

            values.append(
                {
                    "id": str(uuid4()),
                    "commodity_id": commodity_id,
                    "mandi_id": mandi_id,
                    "mandi_name": market,
                    "min_price": min_price,
                    "max_price": max_price,
                    "modal_price": modal_price,
                    "price_date": record_date,
                }
            )

        if not values:
            return 0

        # Bulk insert in batches
        total_upserted = 0
        batch_size = 500
        for i in range(0, len(values), batch_size):
            batch = values[i : i + batch_size]
            total_upserted += self._bulk_upsert_batch(batch, stats)

        return total_upserted

    def _bulk_upsert_batch(
        self, batch: list[dict], stats: ReconciliationStats
    ) -> int:
        """Execute a single batch INSERT … ON CONFLICT."""
        placeholders = []
        params: dict = {}

        for j, v in enumerate(batch):
            p = f"v{j}_"
            placeholders.append(
                f"(:{p}id, :{p}cid, :{p}mid, :{p}mn, "
                f":{p}minp, :{p}maxp, :{p}modp, :{p}pd, NOW(), NOW())"
            )
            params[f"{p}id"] = v["id"]
            params[f"{p}cid"] = v["commodity_id"]
            params[f"{p}mid"] = v["mandi_id"]
            params[f"{p}mn"] = v["mandi_name"]
            params[f"{p}minp"] = v["min_price"]
            params[f"{p}maxp"] = v["max_price"]
            params[f"{p}modp"] = v["modal_price"]
            params[f"{p}pd"] = v["price_date"]

        sql = f"""
            INSERT INTO price_history
                (id, commodity_id, mandi_id, mandi_name,
                 min_price, max_price, modal_price, price_date,
                 created_at, updated_at)
            VALUES {', '.join(placeholders)}
            ON CONFLICT (commodity_id, mandi_name, price_date)
            DO UPDATE SET
                min_price   = EXCLUDED.min_price,
                max_price   = EXCLUDED.max_price,
                modal_price = EXCLUDED.modal_price,
                mandi_id    = EXCLUDED.mandi_id,
                updated_at  = NOW()
        """

        try:
            self.db.execute(text(sql), params)
            self.db.commit()
            stats.records_upserted += len(batch)
            return len(batch)
        except Exception as exc:
            self.db.rollback()
            logger.warning(
                "  Batch upsert error: %s: %s",
                type(exc).__name__,
                str(exc)[:120],
            )
            stats.records_skipped += len(batch)
            stats.errors.append(f"Batch upsert: {exc}")
            return 0

    # ------------------------------------------------------------------
    # Commodity / Mandi helpers (mirrors backfill_prices.py pattern)
    # ------------------------------------------------------------------

    def _load_caches(self) -> None:
        """Pre-load commodity and mandi ID caches from the database."""
        result = self.db.execute(text("SELECT id, name FROM commodities"))
        for row in result:
            self._commodity_cache[row[1]] = str(row[0])

        result = self.db.execute(
            text("SELECT id, name, district, state FROM mandis")
        )
        for row in result:
            key = f"{row[1]}|{row[2]}|{row[3]}"
            self._mandi_cache[key] = str(row[0])

        logger.info(
            "Loaded caches: %d commodities, %d mandis",
            len(self._commodity_cache),
            len(self._mandi_cache),
        )

    def _ensure_commodity(self, name: str, stats: ReconciliationStats) -> str:
        """Get or create a commodity, return its ID."""
        if name in self._commodity_cache:
            return self._commodity_cache[name]

        row = self.db.execute(
            text("SELECT id FROM commodities WHERE name = :name"), {"name": name}
        ).fetchone()
        if row:
            self._commodity_cache[name] = str(row[0])
            return str(row[0])

        new_id = str(uuid4())
        category = _COMMODITY_CATEGORIES.get(name, "Other")
        self.db.execute(
            text("""
                INSERT INTO commodities
                    (id, name, name_local, category, unit, is_active, created_at, updated_at)
                VALUES (:id, :name, :name_local, :cat, 'quintal', true, NOW(), NOW())
                ON CONFLICT (name) DO NOTHING
            """),
            {"id": new_id, "name": name, "name_local": name, "cat": category},
        )
        self.db.commit()

        row = self.db.execute(
            text("SELECT id FROM commodities WHERE name = :name"), {"name": name}
        ).fetchone()
        actual_id = str(row[0])
        self._commodity_cache[name] = actual_id
        stats.new_commodities += 1
        logger.info("  + New commodity: %s (%s)", name, category)
        return actual_id

    def _ensure_mandi(
        self,
        name: str,
        district: str,
        state: str,
        stats: ReconciliationStats,
    ) -> str:
        """Get or create a mandi, return its ID."""
        key = f"{name}|{district}|{state}"
        if key in self._mandi_cache:
            return self._mandi_cache[key]

        row = self.db.execute(
            text(
                "SELECT id FROM mandis "
                "WHERE name = :name AND district = :district AND state = :state"
            ),
            {"name": name, "district": district, "state": state},
        ).fetchone()
        if row:
            self._mandi_cache[key] = str(row[0])
            return str(row[0])

        new_id = str(uuid4())
        code = (
            "".join(c for c in name.upper() if c.isalnum())[:10]
            + str(uuid4())[:4].upper()
        )
        address = f"{name}, {district}, {state}"
        self.db.execute(
            text("""
                INSERT INTO mandis
                    (id, name, market_code, state, district, address,
                     is_active, created_at, updated_at)
                VALUES (:id, :name, :code, :state, :district, :addr,
                        true, NOW(), NOW())
            """),
            {
                "id": new_id, "name": name, "code": code,
                "state": state, "district": district, "addr": address,
            },
        )
        self.db.commit()

        self._mandi_cache[key] = new_id
        stats.new_mandis += 1
        logger.info("  + New mandi: %s, %s, %s", name, district, state)
        return new_id

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _log_gap_summary(summary: GapSummary) -> None:
        actionable = summary.actionable_gaps
        logger.info("=" * 60)
        logger.info("GAP SUMMARY (%s to %s)", summary.period_start, summary.period_end)
        logger.info("-" * 60)
        logger.info("  Total days analysed : %d", summary.total_days)
        logger.info("  Complete            : %d", summary.days_complete)
        logger.info("  Sparse              : %d", summary.days_sparse)
        logger.info("  Missing             : %d", summary.days_missing)
        logger.info("  Weekend/holiday     : %d", summary.days_weekend_holiday)
        logger.info("  Actionable gaps     : %d", len(actionable))
        logger.info("-" * 60)
        for gap in actionable[:20]:
            logger.info("  [%s] %s", gap.severity.upper(), gap.details)
        if len(actionable) > 20:
            logger.info("  ... and %d more", len(actionable) - 20)
        logger.info("=" * 60)
