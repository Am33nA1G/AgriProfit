"""
Fill missing price data from data.gov.in API.

Reads database_gaps_report.json (produced by audit_database_consistency.py)
and fetches data for each date gap with proper rate limiting (1 s between
batched requests) to avoid "too many requests" errors.

Usage:
    cd backend
    python scripts/audit_database_consistency.py   # produces gap report
    python scripts/fill_missing_data.py            # fills gaps
"""
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta, date

# Windows console encoding fix
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Backend root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import func, distinct
from app.database.session import SessionLocal
from app.models import Commodity, Mandi, PriceHistory
from app.integrations.data_gov_client import DataGovClient
from app.integrations.seeder import DatabaseSeeder

# Import the historical API client for backfilling (can fetch per-date data)
from scripts.backfill_prices import BackfillClient, BackfillSeeder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate-limited gap filler
# ---------------------------------------------------------------------------

class RateLimitedDataFiller:
    """Fills date gaps using the existing DataGovClient + DatabaseSeeder."""

    REQUEST_DELAY = 1.0      # seconds between API calls
    BATCH_DAYS    = 10        # days per API request

    def __init__(self):
        self.client = DataGovClient()          # reads key from settings / env
        self.historical_client = BackfillClient()  # historical API for backfilling
        self.db     = SessionLocal()
        self.seeder = DatabaseSeeder(self.db, self.client)
        self.backfill_seeder = BackfillSeeder(self.db)
        self.backfill_seeder.load_caches()
        self._last_request_ts: float = 0.0

        self.stats = {
            "api_requests":       0,
            "api_successes":      0,
            "api_failures":       0,
            "records_fetched":    0,
            "records_created":    0,
            "records_updated":    0,
            "records_skipped":    0,
        }

    # ----- rate limiting --------------------------------------------------

    def _wait_for_rate_limit(self):
        elapsed = time.time() - self._last_request_ts
        if elapsed < self.REQUEST_DELAY:
            wait = self.REQUEST_DELAY - elapsed
            logger.debug(f"Rate-limit: sleeping {wait:.2f}s")
            time.sleep(wait)

    # ----- fetch a date batch ---------------------------------------------

    def _fetch_batch(self, from_date: date, to_date: date) -> list[dict]:
        """Fetch records for a date range using the historical API resource.

        Uses BackfillClient which accesses the historical resource
        (35985678-0d79-46b4-9ed6-6f13308a1d24) with filters[Arrival_Date]
        for per-day fetching. This is the correct approach for backfilling
        gaps, as the daily resource only returns today's snapshot.
        """
        all_records: list[dict] = []
        current = from_date

        while current <= to_date:
            self._wait_for_rate_limit()
            self.stats["api_requests"] += 1
            date_str = current.strftime("%d/%m/%Y")

            try:
                records = self.historical_client.fetch_all_for_date(date_str)
                all_records.extend(records)
                self.stats["api_successes"] += 1
                self.stats["records_fetched"] += len(records)
                logger.info(
                    f"  Fetched {len(records)} records for {current} "
                    f"from historical API"
                )
                self._last_request_ts = time.time()
            except Exception as exc:
                self.stats["api_failures"] += 1
                logger.warning(f"  API request failed for {current}: {exc}")
                self._last_request_ts = time.time()

            current += timedelta(days=1)
            # Rate limit between days
            if current <= to_date:
                time.sleep(5.0)

        return all_records

    @staticmethod
    def _filter_by_date(records: list[dict], from_d: date, to_d: date) -> list[dict]:
        """Keep only records whose arrival_date falls in [from_d, to_d]."""
        out = []
        for r in records:
            raw = r.get("arrival_date", "")
            try:
                dt = datetime.strptime(raw, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                continue
            if from_d <= dt <= to_d:
                out.append(r)
        return out

    # ----- seed a batch into the DB via the existing seeder ---------------

    def _seed_records(self, records: list[dict]):
        """Seed records using BackfillSeeder for historical data (per-date).

        Groups records by date and uses BackfillSeeder.seed_day() which
        handles bulk INSERT with ON CONFLICT for efficient deduplication.
        """
        if not records:
            return

        # Group records by date for BackfillSeeder
        from collections import defaultdict
        from datetime import datetime as dt

        records_by_date = defaultdict(list)
        for r in records:
            date_str = str(r.get("Arrival_Date", r.get("arrival_date", ""))).strip()
            if not date_str:
                continue
            try:
                record_date = dt.strptime(date_str, "%d/%m/%Y").date()
                records_by_date[record_date].append(r)
            except (ValueError, TypeError):
                continue

        total_created = 0
        for target_date, day_records in sorted(records_by_date.items()):
            created = self.backfill_seeder.seed_day(day_records, target_date)
            total_created += created

        self.stats["records_created"] += total_created
        self.stats["records_skipped"] += len(records) - total_created

    # ----- main public methods --------------------------------------------

    def fill_date_gaps(self, gaps: list[dict]):
        """Fill all date gaps listed in the report."""
        if not gaps:
            logger.info("No date gaps to fill.")
            return

        total_days = sum(g["days"] for g in gaps)
        logger.info(f"Filling {len(gaps)} gap(s) totalling {total_days} day(s)...")

        for idx, gap in enumerate(gaps, 1):
            gap_start = date.fromisoformat(gap["start"])
            gap_end   = date.fromisoformat(gap["end"])
            gap_days  = gap["days"]
            logger.info(
                f"\n--- Gap {idx}/{len(gaps)}: "
                f"{gap_start} -> {gap_end} ({gap_days} day(s)) ---"
            )

            current = gap_start
            while current <= gap_end:
                batch_end = min(current + timedelta(days=self.BATCH_DAYS - 1), gap_end)
                logger.info(f"  Batch: {current} -> {batch_end}")

                records = self._fetch_batch(current, batch_end)
                self._seed_records(records)

                current = batch_end + timedelta(days=1)

            # Commit per gap
            self.db.commit()
            logger.info(f"  Gap {idx} committed.")

    def fill_from_current_api(self):
        """
        Fetch whatever the API currently returns (typically 'today's data')
        and upsert it.  Useful when the gap report shows the DB is stale but
        the API doesn't support date-range filtering.
        """
        logger.info("Fetching current API snapshot and upserting...")
        self._wait_for_rate_limit()
        self.stats["api_requests"] += 1

        try:
            records = self.client.fetch_all_prices(batch_size=1000)
            self.stats["api_successes"] += 1
            self.stats["records_fetched"] += len(records)
            logger.info(f"Fetched {len(records)} records from API.")
            self._seed_records(records)
            self.db.commit()
        except Exception as exc:
            self.stats["api_failures"] += 1
            logger.error(f"Full-fetch failed: {exc}", exc_info=True)
            self.db.rollback()

    def print_summary(self):
        print("\n" + "=" * 80)
        print("  DATA FILL SUMMARY")
        print("=" * 80)
        for k, v in self.stats.items():
            label = k.replace("_", " ").title()
            print(f"   {label:30s} {v:>10,}")

        if self.stats["api_requests"]:
            rate = self.stats["api_successes"] / self.stats["api_requests"] * 100
            print(f"\n   API Success Rate            {rate:>9.1f}%")

    def close(self):
        self.client.close()
        self.historical_client.close()
        self.db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 80)
    print("  FILL MISSING DATABASE DATA")
    print("=" * 80)
    print(f"  Started : {datetime.now()}")
    print(f"  Rate    : 1 request / {RateLimitedDataFiller.REQUEST_DELAY}s\n")

    report_path = Path(__file__).resolve().parent.parent / "database_gaps_report.json"
    if not report_path.exists():
        print(f"ERROR: {report_path} not found.")
        print("       Run  audit_database_consistency.py  first.")
        return False

    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    summary = report.get("summary", {})
    print(f"  Gap report loaded:")
    print(f"    Date gaps             : {summary.get('total_date_gaps', 0)}")
    print(f"    Total missing days    : {summary.get('total_days_missing', 0)}")
    print(f"    Commodities w/o prices: {summary.get('commodities_without_prices', 0)}")
    print(f"    Mandis w/o prices     : {summary.get('mandis_without_prices', 0)}")

    filler = RateLimitedDataFiller()

    try:
        # 1) Fill date gaps (targeted)
        filler.fill_date_gaps(report.get("date_gaps", []))

        # 2) Also do a fresh pull of today's data so the DB is up-to-date
        filler.fill_from_current_api()

        filler.print_summary()
        print(f"\n  Finished: {datetime.now()}")
        return True

    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        filler.db.rollback()
        filler.print_summary()
        return False

    except Exception as exc:
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        filler.db.rollback()
        filler.print_summary()
        return False

    finally:
        filler.close()


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
