#!/usr/bin/env python3
"""
ETL Script: Migrate historical price data from Parquet to PostgreSQL.

Reads the agmarknet_daily_10yr.parquet file and bulk-loads records into
the price_history table.  Commodities and mandis that don't already exist
in the database are created automatically.

Usage:
    python scripts/etl_parquet_to_postgres.py                # full migration
    python scripts/etl_parquet_to_postgres.py --dry-run      # preview only
    python scripts/etl_parquet_to_postgres.py --batch-size 5000
    python scripts/etl_parquet_to_postgres.py --limit 100000 # test with subset

Options:
    --dry-run           Preview what would happen without writing to DB
    --batch-size N      Rows per INSERT batch (default: 10000)
    --limit N           Only process first N rows (for testing)
    --skip-validation   Skip data-quality checks (faster but risky)
    --force             Don't prompt when existing data is found
    --parquet-path P    Path to the Parquet file
"""

import argparse
import os
import sys
import uuid as uuid_module
from datetime import datetime, date as date_type
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Add project root to sys.path so we can import app.*
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # backend/
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.session import SessionLocal, engine
from app.models.commodity import Commodity
from app.models.mandi import Mandi
from app.models.price_history import PriceHistory

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_PARQUET = str(PROJECT_ROOT.parent / "agmarknet_daily_10yr.parquet")
DEFAULT_BATCH_SIZE = 10_000
LOG_DIR = PROJECT_ROOT / "logs"
MAX_INSERT_PARAMS = 60_000


# ============================================================================
# Logger
# ============================================================================

class ETLLogger:
    """File + stdout logger."""

    def __init__(self, log_file: Path):
        log_file.parent.mkdir(parents=True, exist_ok=True)
        self._path = log_file
        # Truncate on start
        self._path.write_text("", encoding="utf-8")

    def log(self, message: str, level: str = "INFO") -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level}] {message}"
        print(line)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


# ============================================================================
# ETL Pipeline
# ============================================================================

class ParquetToPostgresETL:
    def __init__(
        self,
        parquet_path: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        limit: int | None = None,
        dry_run: bool = False,
        skip_validation: bool = False,
        force: bool = False,
    ):
        self.parquet_path = parquet_path
        self.batch_size = batch_size
        self.limit = limit
        self.dry_run = dry_run
        self.skip_validation = skip_validation
        self.force = force

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = ETLLogger(LOG_DIR / f"etl_{ts}.log")
        self.log_file = LOG_DIR / f"etl_{ts}.log"

        self.db = SessionLocal()

        # Caches:  lowercase name -> UUID
        self.commodity_cache: dict[str, uuid_module.UUID] = {}
        # (state_lower, district_lower) -> UUID
        self.mandi_cache: dict[tuple[str, str], uuid_module.UUID] = {}

        self.stats = {
            "total_parquet_rows": 0,
            "rows_after_validation": 0,
            "inserted": 0,
            "duplicates_skipped": 0,
            "batches_failed": 0,
            "rows_in_failed_batches": 0,
            "commodities_created": 0,
            "mandis_created": 0,
            "start_time": datetime.now(),
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        try:
            self._banner("STARTING ETL: Parquet -> PostgreSQL")
            self._preflight()
            self._load_caches()
            df = self._read_parquet()
            if not self.skip_validation:
                df = self._validate(df)
            self.stats["rows_after_validation"] = len(df)
            df = self._resolve_foreign_keys(df)
            self._insert_batches(df)
            self._report()
            self._banner("ETL COMPLETE")
        except KeyboardInterrupt:
            self.logger.log("Interrupted by user", "WARN")
            self._report()
        except Exception as exc:
            self.logger.log(f"FATAL: {exc}", "ERROR")
            self._report()
            raise
        finally:
            self.db.close()

    # ------------------------------------------------------------------
    # Step 1 - Preflight checks
    # ------------------------------------------------------------------

    def _preflight(self) -> None:
        self.logger.log("Running preflight checks ...")

        # File exists?
        p = Path(self.parquet_path)
        if not p.exists():
            raise FileNotFoundError(f"Parquet file not found: {p}")
        self.logger.log(f"  File size: {p.stat().st_size / (1024*1024):.1f} MB")

        # DB alive?
        try:
            self.db.execute(text("SELECT 1"))
            self.logger.log("  Database connection: OK")
        except Exception as exc:
            raise ConnectionError(f"Database unreachable: {exc}") from exc

        # Existing rows
        existing = self.db.execute(
            text("SELECT COUNT(*) FROM price_history")
        ).scalar() or 0
        self.logger.log(f"  Existing price_history rows: {existing:,}")

        if existing > 0 and not self.force and not self.dry_run:
            answer = input(
                f"\n  {existing:,} rows already in price_history. "
                "Continue? Duplicates will be skipped. (yes/no): "
            )
            if answer.strip().lower() != "yes":
                self.logger.log("Cancelled by user.")
                sys.exit(0)

        self.logger.log("  Preflight OK")

    # ------------------------------------------------------------------
    # Step 2 - Load reference-data caches
    # ------------------------------------------------------------------

    def _load_caches(self) -> None:
        self.logger.log("Loading reference data caches ...")

        for c in self.db.query(Commodity.id, Commodity.name).all():
            self.commodity_cache[c.name.strip().lower()] = c.id
        self.logger.log(f"  Cached {len(self.commodity_cache)} commodities")

        for m in self.db.query(Mandi.id, Mandi.state, Mandi.district).all():
            key = (m.state.strip().lower(), m.district.strip().lower())
            self.mandi_cache[key] = m.id
        self.logger.log(f"  Cached {len(self.mandi_cache)} mandis")

    # ------------------------------------------------------------------
    # Step 3 - Read Parquet
    # ------------------------------------------------------------------

    def _read_parquet(self) -> pd.DataFrame:
        self.logger.log(f"Reading {self.parquet_path} ...")
        df = pd.read_parquet(self.parquet_path, engine="pyarrow")
        self.stats["total_parquet_rows"] = len(df)
        self.logger.log(f"  Loaded {len(df):,} rows, columns: {list(df.columns)}")

        if self.limit:
            df = df.head(self.limit)
            self.logger.log(f"  --limit applied: using first {len(df):,} rows")

        return df

    # ------------------------------------------------------------------
    # Step 4 - Validate / clean
    # ------------------------------------------------------------------

    def _validate(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.log("Validating data ...")
        before = len(df)

        # Required columns
        required = {"date", "commodity", "state", "district", "price_modal"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Drop rows where critical fields are null
        df = df.dropna(subset=["date", "commodity", "state", "district", "price_modal"])
        dropped_nulls = before - len(df)
        if dropped_nulls:
            self.logger.log(f"  Dropped {dropped_nulls:,} rows with null critical fields")

        # Drop rows with non-positive modal price
        bad_price_mask = df["price_modal"] <= 0
        bad_prices = int(bad_price_mask.sum())
        if bad_prices:
            df = df[~bad_price_mask]
            self.logger.log(f"  Dropped {bad_prices:,} rows with modal_price <= 0")

        # Drop rows with price > 10,000,000 (likely data errors)
        extreme_mask = df["price_modal"] > 10_000_000
        extreme = int(extreme_mask.sum())
        if extreme:
            df = df[~extreme_mask]
            self.logger.log(f"  Dropped {extreme:,} rows with extreme modal_price")

        self.logger.log(f"  Validation done: {len(df):,} rows remain (dropped {before - len(df):,})")
        return df

    # ------------------------------------------------------------------
    # Step 5 - Resolve / create foreign keys
    # ------------------------------------------------------------------

    def _resolve_foreign_keys(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.log("Resolving foreign keys ...")

        # --- Commodities ---------------------------------------------------
        unique_commodities = df["commodity"].dropna().unique()
        new_commodities = [
            c for c in unique_commodities if c.strip().lower() not in self.commodity_cache
        ]
        if new_commodities:
            self.logger.log(f"  Creating {len(new_commodities)} new commodity records ...")
            for name in new_commodities:
                obj = Commodity(id=uuid_module.uuid4(), name=name.strip())
                self.db.add(obj)
                self.commodity_cache[name.strip().lower()] = obj.id
            self.db.commit()
            self.stats["commodities_created"] = len(new_commodities)
            self.logger.log(f"  Created {len(new_commodities)} commodities")

        # Map commodity name -> UUID
        df["_commodity_id"] = df["commodity"].str.strip().str.lower().map(self.commodity_cache)

        # --- Mandis --------------------------------------------------------
        mandi_pairs = (
            df[["state", "district", "state_id", "district_id"]]
            .drop_duplicates(subset=["state", "district"])
        )
        new_mandis = []
        for _, row in mandi_pairs.iterrows():
            key = (str(row["state"]).strip().lower(), str(row["district"]).strip().lower())
            if key not in self.mandi_cache:
                new_mandis.append(row)

        if new_mandis:
            self.logger.log(f"  Creating {len(new_mandis)} new mandi records ...")
            for row in new_mandis:
                state = str(row["state"]).strip()
                district = str(row["district"]).strip()
                state_id = row.get("state_id", 0)
                district_id = row.get("district_id", 0)
                market_code = f"AGM_{int(state_id)}_{int(district_id)}"

                obj = Mandi(
                    id=uuid_module.uuid4(),
                    name=district,
                    state=state,
                    district=district,
                    market_code=market_code,
                )
                self.db.add(obj)
                self.mandi_cache[(state.lower(), district.lower())] = obj.id
            self.db.commit()
            self.stats["mandis_created"] = len(new_mandis)
            self.logger.log(f"  Created {len(new_mandis)} mandis")

        # Map (state, district) -> UUID
        def _lookup_mandi(row: pd.Series) -> Any:
            key = (str(row["state"]).strip().lower(), str(row["district"]).strip().lower())
            return self.mandi_cache.get(key)

        df["_mandi_id"] = df.apply(_lookup_mandi, axis=1)

        # Drop rows where FK resolution failed (should be 0 after auto-create)
        fk_missing = df["_commodity_id"].isna() | df["_mandi_id"].isna()
        n_missing = int(fk_missing.sum())
        if n_missing:
            self.logger.log(f"  WARNING: {n_missing:,} rows with unresolved FKs dropped", "WARN")
            df = df[~fk_missing]

        self.logger.log(f"  Foreign keys resolved for {len(df):,} rows")
        return df

    # ------------------------------------------------------------------
    # Step 6 - Batch insert
    # ------------------------------------------------------------------

    def _insert_batches(self, df: pd.DataFrame) -> None:
        total = len(df)
        n_batches = (total + self.batch_size - 1) // self.batch_size
        self.logger.log(
            f"Inserting {total:,} rows in {n_batches:,} batches "
            f"(batch_size={self.batch_size:,}) ..."
        )

        if self.dry_run:
            self.logger.log("DRY RUN - no rows written to database")
            self.stats["inserted"] = total
            return

        table = PriceHistory.__table__

        for batch_idx in range(n_batches):
            start = batch_idx * self.batch_size
            end = min(start + self.batch_size, total)
            chunk = df.iloc[start:end]

            records = self._chunk_to_dicts(chunk)
            if not records:
                continue

            max_rows_per_insert = self._max_rows_per_insert(records)
            if len(records) > max_rows_per_insert and batch_idx == 0:
                self.logger.log(
                    f"  Batch size {len(records):,} exceeds parameter-safe insert size; "
                    f"splitting into sub-batches of {max_rows_per_insert:,}",
                    "WARN",
                )

            for sub_start in range(0, len(records), max_rows_per_insert):
                sub_records = records[sub_start:sub_start + max_rows_per_insert]
                try:
                    stmt = pg_insert(table).values(sub_records)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=["commodity_id", "mandi_name", "price_date"]
                    )
                    result = self.db.execute(stmt)
                    self.db.commit()

                    inserted = result.rowcount if result.rowcount >= 0 else len(sub_records)
                    skipped = len(sub_records) - inserted
                    self.stats["inserted"] += inserted
                    self.stats["duplicates_skipped"] += skipped

                except Exception as exc:
                    self.db.rollback()
                    self.stats["batches_failed"] += 1
                    self.stats["rows_in_failed_batches"] += len(sub_records)
                    self.logger.log(
                        f"  Batch {batch_idx + 1} FAILED ({len(sub_records)} rows): {exc}",
                        "ERROR",
                    )

            # Progress every 50 batches or on last batch
            if (batch_idx + 1) % 50 == 0 or batch_idx + 1 == n_batches:
                pct = (end / total) * 100
                self.logger.log(
                    f"  Progress: {end:,}/{total:,} ({pct:.1f}%) | "
                    f"inserted={self.stats['inserted']:,}  "
                    f"dup_skip={self.stats['duplicates_skipped']:,}  "
                    f"failed_batches={self.stats['batches_failed']}"
                )

    @staticmethod
    def _max_rows_per_insert(records: list[dict]) -> int:
        if not records:
            return 1
        params_per_row = max(len(records[0]), 1)
        return max(1, MAX_INSERT_PARAMS // params_per_row)

    def _chunk_to_dicts(self, chunk: pd.DataFrame) -> list[dict]:
        """Convert a DataFrame chunk to a list of dicts for bulk insert."""
        records: list[dict] = []
        for _, row in chunk.iterrows():
            try:
                # Convert prices safely
                modal = self._to_decimal(row["price_modal"])
                if modal is None or modal <= 0:
                    continue

                min_p = self._to_decimal(row.get("price_min"))
                max_p = self._to_decimal(row.get("price_max"))

                # Ensure min <= modal <= max when all are present
                if min_p is not None and min_p > modal:
                    min_p = modal
                if max_p is not None and max_p < modal:
                    max_p = modal

                # Convert date
                price_date = pd.Timestamp(row["date"]).date()

                records.append(
                    {
                        "id": uuid_module.uuid4(),
                        "commodity_id": row["_commodity_id"],
                        "mandi_id": row["_mandi_id"],
                        "mandi_name": str(row["district"]).strip(),
                        "price_date": price_date,
                        "modal_price": modal,
                        "min_price": min_p,
                        "max_price": max_p,
                    }
                )
            except Exception:
                # Skip malformed rows silently
                continue

        return records

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        """Safely convert a value to Decimal(10,2), returning None on failure."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        try:
            d = Decimal(str(float(value))).quantize(Decimal("0.01"))
            return d if d >= 0 else None
        except (InvalidOperation, ValueError, TypeError, OverflowError):
            return None

    # ------------------------------------------------------------------
    # Step 7 - Report
    # ------------------------------------------------------------------

    def _report(self) -> None:
        end = datetime.now()
        duration = end - self.stats["start_time"]
        secs = max(duration.total_seconds(), 0.01)

        # Final DB count
        try:
            final_count = self.db.execute(
                text("SELECT COUNT(*) FROM price_history")
            ).scalar() or 0
        except Exception:
            final_count = "?"

        report = f"""
{'=' * 72}
  ETL MIGRATION REPORT
{'=' * 72}

  Start:    {self.stats['start_time']:%Y-%m-%d %H:%M:%S}
  End:      {end:%Y-%m-%d %H:%M:%S}
  Duration: {duration}

  Input
    Total Parquet rows:          {self.stats['total_parquet_rows']:>14,}
    Rows after validation:       {self.stats['rows_after_validation']:>14,}

  Reference Data Created
    New commodities:             {self.stats['commodities_created']:>14,}
    New mandis:                  {self.stats['mandis_created']:>14,}

  Results
    Inserted:                    {self.stats['inserted']:>14,}
    Duplicates skipped:          {self.stats['duplicates_skipped']:>14,}
    Failed batches:              {self.stats['batches_failed']:>14,}
    Rows in failed batches:      {self.stats['rows_in_failed_batches']:>14,}

  Database
    Final price_history count:   {str(final_count):>14s}

  Performance
    Rows/sec (inserted):         {self.stats['inserted'] / secs:>14,.0f}

  Log file: {self.log_file}
{'=' * 72}
"""
        print(report)
        # Also write to a summary file
        summary_path = self.log_file.with_suffix(".summary.txt")
        summary_path.write_text(report, encoding="utf-8")
        self.logger.log(f"Summary saved to {summary_path}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _banner(self, msg: str) -> None:
        self.logger.log("=" * 72)
        self.logger.log(msg)
        self.logger.log("=" * 72)


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETL: Parquet -> PostgreSQL (price_history)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=None, help="Process only first N rows")
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--force", action="store_true", help="Don't prompt on existing data")
    parser.add_argument("--parquet-path", default=DEFAULT_PARQUET)

    args = parser.parse_args()

    etl = ParquetToPostgresETL(
        parquet_path=args.parquet_path,
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
        skip_validation=args.skip_validation,
        force=args.force,
    )
    etl.run()


if __name__ == "__main__":
    main()
