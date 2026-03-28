"""
Data Sync Service

Wraps the database seeder with sync status tracking, error reporting,
and summary statistics. Used by both the background scheduler and the
manual sync CLI script.
"""
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from app.database.session import SessionLocal
from app.integrations.data_gov_client import get_data_gov_client
from app.integrations.seeder import DatabaseSeeder
from app.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class SyncResult:
    """Result of a single sync run."""
    status: SyncStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    records_fetched: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class SyncState:
    """Tracks the current and historical sync state."""
    current_status: SyncStatus = SyncStatus.IDLE
    last_sync: Optional[SyncResult] = None
    total_syncs: int = 0
    total_failures: int = 0
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None


class DataSyncService:
    """
    Service for syncing price data from data.gov.in to PostgreSQL.

    Thread-safe singleton that tracks sync status and prevents
    concurrent sync runs.
    """

    _instance: Optional["DataSyncService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "DataSyncService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._state = SyncState()
        self._sync_lock = threading.Lock()
        self._restore_state()

    def _restore_state(self) -> None:
        """Restore sync state from the sync_log table on startup."""
        try:
            from sqlalchemy import select, desc
            db = SessionLocal()
            try:
                # Restore last_success_at
                last_success = db.execute(
                    select(SyncLog)
                    .where(SyncLog.status == "success")
                    .order_by(desc(SyncLog.finished_at))
                    .limit(1)
                ).scalar_one_or_none()

                if last_success:
                    self._state.last_success_at = last_success.finished_at
                    logger.info(
                        "Restored last_success_at from DB: %s",
                        last_success.finished_at,
                    )

                # Restore last_failure_at
                last_failure = db.execute(
                    select(SyncLog)
                    .where(SyncLog.status == "failed")
                    .order_by(desc(SyncLog.finished_at))
                    .limit(1)
                ).scalar_one_or_none()

                if last_failure:
                    self._state.last_failure_at = last_failure.finished_at

                # Restore counters
                from sqlalchemy import func
                totals = db.execute(
                    select(
                        func.count().label("total"),
                        func.count()
                        .filter(SyncLog.status == "failed")
                        .label("failures"),
                    ).select_from(SyncLog)
                ).one()

                self._state.total_syncs = totals.total
                self._state.total_failures = totals.failures
            finally:
                db.close()
        except Exception as e:
            logger.warning("Could not restore sync state from DB: %s", e)

    def _persist_result(self, result: "SyncResult") -> None:
        """Write a sync result row to the sync_log table."""
        try:
            db = SessionLocal()
            try:
                row = SyncLog(
                    status=result.status.value,
                    started_at=result.started_at,
                    finished_at=result.finished_at,
                    records_fetched=result.records_fetched,
                    duration_seconds=result.duration_seconds,
                    error=result.error,
                )
                db.add(row)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning("Could not persist sync result to DB: %s", e)

    @property
    def state(self) -> SyncState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state.current_status == SyncStatus.RUNNING

    def sync(self, limit: Optional[int] = None) -> SyncResult:
        """
        Run a price data sync.

        Fetches latest prices from data.gov.in and upserts them into
        the database. Prevents concurrent runs via a lock.

        Args:
            limit: Optional record limit (for testing). None fetches all.

        Returns:
            SyncResult with summary statistics.
        """
        if not self._sync_lock.acquire(blocking=False):
            logger.warning("Sync already in progress, skipping")
            return SyncResult(
                status=SyncStatus.RUNNING,
                started_at=datetime.now(),
                error="Sync already in progress",
            )

        result = SyncResult(
            status=SyncStatus.RUNNING,
            started_at=datetime.now(),
        )
        self._state.current_status = SyncStatus.RUNNING

        try:
            logger.info("Starting price data sync from data.gov.in...")

            client = get_data_gov_client()

            if limit:
                # Test mode — fetch a single page
                data = client.fetch_prices(limit=limit)
                records = data.get("records", [])
                result.records_fetched = len(records)
                logger.info(f"Fetched {result.records_fetched} records from API")
                if records:
                    db = SessionLocal()
                    try:
                        seeder = DatabaseSeeder(db, client)
                        seeder.seed_all(records=records)
                    finally:
                        db.close()
            elif self._state.last_success_at:
                # Incremental sync with per-date checkpoints
                result.records_fetched = self._sync_incremental(client)
            else:
                # Full fetch (first run — no prior sync)
                records = client.fetch_all_prices()
                result.records_fetched = len(records)
                logger.info(f"Fetched {result.records_fetched} records from API")
                if records:
                    db = SessionLocal()
                    try:
                        seeder = DatabaseSeeder(db, client)
                        seeder.seed_all(records=records)
                    finally:
                        db.close()

            if not result.records_fetched:
                logger.warning("No records fetched from API")

            result.status = SyncStatus.SUCCESS
            logger.info(
                f"Sync completed: {result.records_fetched} records processed"
            )

        except Exception as e:
            result.status = SyncStatus.FAILED
            result.error = str(e)
            logger.error(f"Sync failed: {e}", exc_info=True)

        finally:
            result.finished_at = datetime.now()
            result.duration_seconds = (
                result.finished_at - result.started_at
            ).total_seconds()
            self._update_state(result)
            self._sync_lock.release()

        return result

    def _sync_incremental(self, client) -> int:
        """Per-date incremental sync with checkpoint/resume.

        Processes each date as an atomic unit: fetch -> seed -> checkpoint.
        If interrupted, the next run resumes from the last completed date.
        """
        from app.core.config import settings

        last = self._state.last_success_at
        # Strip timezone info so subtraction works regardless of
        # whether the DB value is offset-aware or naive.
        last_naive = last.replace(tzinfo=None) if last.tzinfo else last
        today = datetime.now()

        days_since = (today - last_naive).days + 1
        max_days = settings.sync_lookback_days
        days_to_fetch = min(days_since, max_days)

        dates = [today - timedelta(days=i) for i in range(days_to_fetch)]
        dates.reverse()  # oldest first

        logger.info(
            "Incremental sync: %d day(s) from %s to %s",
            days_to_fetch,
            dates[0].strftime("%d/%m/%Y"),
            dates[-1].strftime("%d/%m/%Y"),
        )

        total_fetched = 0
        db = SessionLocal()
        try:
            seeder = DatabaseSeeder(db, client)
            seeder.preload_caches()

            for dt in dates:
                date_str = dt.strftime("%d/%m/%Y")

                # Fetch all records for this single date
                records = client.fetch_prices_for_dates([dt])

                if not records:
                    logger.info("No records for %s, skipping", date_str)
                    continue

                # Seed this date's records (atomic per-date)
                seeder.seed_records(records)
                total_fetched += len(records)

                # Checkpoint: advance last_success_at so a crash
                # resumes from here
                self._state.last_success_at = dt

                logger.info(
                    "Checkpoint: %s complete (%d records, %d total)",
                    date_str, len(records), total_fetched,
                )
        finally:
            db.close()

        return total_fetched

    def _update_state(self, result: SyncResult) -> None:
        """Update internal sync state after a run and persist to DB."""
        self._state.current_status = (
            SyncStatus.IDLE if result.status != SyncStatus.RUNNING
            else SyncStatus.RUNNING
        )
        self._state.last_sync = result
        self._state.total_syncs += 1

        if result.status == SyncStatus.SUCCESS:
            self._state.last_success_at = result.finished_at
        elif result.status == SyncStatus.FAILED:
            self._state.total_failures += 1
            self._state.last_failure_at = result.finished_at

        # Persist to DB so state survives restarts
        self._persist_result(result)

    def get_status_dict(self) -> dict:
        """Return sync status as a JSON-serializable dict."""
        state = self._state
        last = state.last_sync

        return {
            "status": state.current_status.value,
            "total_syncs": state.total_syncs,
            "total_failures": state.total_failures,
            "last_success_at": (
                state.last_success_at.isoformat()
                if state.last_success_at else None
            ),
            "last_failure_at": (
                state.last_failure_at.isoformat()
                if state.last_failure_at else None
            ),
            "last_sync": {
                "status": last.status.value,
                "started_at": last.started_at.isoformat(),
                "finished_at": (
                    last.finished_at.isoformat() if last.finished_at else None
                ),
                "records_fetched": last.records_fetched,
                "duration_seconds": round(last.duration_seconds, 2),
                "error": last.error,
            } if last else None,
        }


def get_sync_service() -> DataSyncService:
    """Get the singleton DataSyncService instance."""
    return DataSyncService()
