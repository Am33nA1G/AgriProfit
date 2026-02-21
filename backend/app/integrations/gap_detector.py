"""
Data gap detection service.

Identifies missing price records in the price_history table using SQL analysis.
Used by the DataReconciler to determine which dates/commodities need backfilling.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Indian market holidays (fixed dates; approximate for variable ones)
# Markets are generally closed on Sundays and national holidays.
KNOWN_HOLIDAYS_MMDD = {
    "01-26",  # Republic Day
    "08-15",  # Independence Day
    "10-02",  # Gandhi Jayanti
}


@dataclass
class DataGap:
    """Represents a detected data gap."""

    gap_type: str  # 'complete', 'sparse', 'commodity'
    gap_date: date
    severity: str = "medium"  # 'low', 'medium', 'high'
    record_count: int = 0
    expected_min: int = 0
    commodity_name: Optional[str] = None
    details: str = ""

    def __repr__(self) -> str:
        return f"<DataGap {self.gap_type} {self.gap_date} severity={self.severity}>"


@dataclass
class GapSummary:
    """Summary of a gap detection run."""

    period_start: date
    period_end: date
    total_days: int = 0
    days_complete: int = 0
    days_sparse: int = 0
    days_missing: int = 0
    days_weekend_holiday: int = 0
    gaps: List[DataGap] = field(default_factory=list)

    @property
    def gap_count(self) -> int:
        return len(self.gaps)

    @property
    def actionable_gaps(self) -> List[DataGap]:
        """Gaps worth attempting to fill (high and medium severity)."""
        return [g for g in self.gaps if g.severity in ("high", "medium")]


def _is_expected_closure(d: date) -> bool:
    """Check if a date is a Sunday or known national holiday."""
    if d.weekday() == 6:  # Sunday
        return True
    mmdd = d.strftime("%m-%d")
    return mmdd in KNOWN_HOLIDAYS_MMDD


class GapDetector:
    """Detects missing data in the price_history table."""

    # Days with fewer records than this are considered sparse
    DEFAULT_SPARSE_THRESHOLD = 500

    def __init__(self, db: Session):
        self.db = db

    def detect_gaps(
        self,
        start_date: date,
        end_date: date,
        sparse_threshold: int = DEFAULT_SPARSE_THRESHOLD,
    ) -> GapSummary:
        """
        Detect all date-level gaps in the given range.

        Args:
            start_date: Start of analysis period.
            end_date: End of analysis period.
            sparse_threshold: Minimum records/day to consider "complete".

        Returns:
            GapSummary with classified gaps.
        """
        summary = GapSummary(period_start=start_date, period_end=end_date)

        # Query daily record counts
        daily_counts = self._get_daily_counts(start_date, end_date)

        current = start_date
        while current <= end_date:
            summary.total_days += 1
            count = daily_counts.get(current, 0)

            if _is_expected_closure(current):
                summary.days_weekend_holiday += 1
                current += timedelta(days=1)
                continue

            if count == 0:
                summary.days_missing += 1
                summary.gaps.append(
                    DataGap(
                        gap_type="complete",
                        gap_date=current,
                        severity="high",
                        record_count=0,
                        expected_min=sparse_threshold,
                        details=f"No records on {current}",
                    )
                )
            elif count < sparse_threshold:
                summary.days_sparse += 1
                summary.gaps.append(
                    DataGap(
                        gap_type="sparse",
                        gap_date=current,
                        severity="medium",
                        record_count=count,
                        expected_min=sparse_threshold,
                        details=f"Only {count} records on {current} (expected >= {sparse_threshold})",
                    )
                )
            else:
                summary.days_complete += 1

            current += timedelta(days=1)

        logger.info(
            "Gap detection complete: %d days analysed, %d complete, "
            "%d sparse, %d missing, %d weekend/holiday",
            summary.total_days,
            summary.days_complete,
            summary.days_sparse,
            summary.days_missing,
            summary.days_weekend_holiday,
        )
        return summary

    def detect_commodity_gaps(
        self,
        start_date: date,
        end_date: date,
        commodity_names: Optional[List[str]] = None,
        min_days_present: int = 5,
    ) -> List[DataGap]:
        """
        Detect commodities with unusually few data days in the range.

        Args:
            start_date: Start of analysis period.
            end_date: End of analysis period.
            commodity_names: If provided, only check these. Otherwise check top-10
                by historical volume.
            min_days_present: Minimum days a commodity should appear.

        Returns:
            List of commodity-level gaps.
        """
        if commodity_names is None:
            commodity_names = [
                "Rice", "Wheat", "Tomato", "Onion", "Potato",
                "Maize", "Groundnut", "Soyabean", "Cotton", "Sugarcane",
            ]

        result = self.db.execute(
            text("""
                SELECT
                    c.name,
                    COUNT(DISTINCT ph.price_date) AS days_present,
                    MIN(ph.price_date)            AS first_date,
                    MAX(ph.price_date)            AS last_date
                FROM commodities c
                LEFT JOIN price_history ph
                    ON c.id = ph.commodity_id
                   AND ph.price_date >= :start
                   AND ph.price_date <= :end
                WHERE c.name = ANY(:names)
                GROUP BY c.name
                ORDER BY days_present ASC
            """),
            {"start": start_date, "end": end_date, "names": commodity_names},
        )

        # Count expected working days in range
        expected_days = sum(
            1
            for i in range((end_date - start_date).days + 1)
            if not _is_expected_closure(start_date + timedelta(days=i))
        )

        gaps: List[DataGap] = []
        for row in result:
            name, days_present, first, last = row
            days_present = days_present or 0
            if days_present < min_days_present:
                gaps.append(
                    DataGap(
                        gap_type="commodity",
                        gap_date=start_date,
                        severity="high" if days_present == 0 else "medium",
                        record_count=days_present,
                        expected_min=expected_days,
                        commodity_name=name,
                        details=(
                            f"{name}: {days_present}/{expected_days} days with data "
                            f"({start_date} to {end_date})"
                        ),
                    )
                )

        return gaps

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_daily_counts(self, start_date: date, end_date: date) -> Dict[date, int]:
        """Return {date: record_count} for the range."""
        result = self.db.execute(
            text("""
                SELECT price_date, COUNT(*) AS cnt
                FROM price_history
                WHERE price_date >= :start AND price_date <= :end
                GROUP BY price_date
                ORDER BY price_date
            """),
            {"start": start_date, "end": end_date},
        )
        return {row[0]: row[1] for row in result}

    def get_date_stats(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Return per-date statistics for display / reporting.

        Each dict has keys: date, records, commodities, mandis, status.
        """
        result = self.db.execute(
            text("""
                SELECT
                    price_date,
                    COUNT(*)                    AS record_count,
                    COUNT(DISTINCT commodity_id) AS commodity_count,
                    COUNT(DISTINCT mandi_id)     AS mandi_count
                FROM price_history
                WHERE price_date >= :start AND price_date <= :end
                GROUP BY price_date
                ORDER BY price_date DESC
            """),
            {"start": start_date, "end": end_date},
        )

        stats = []
        for row in result:
            d, records, commodities, mandis = row
            if records == 0:
                status = "COMPLETE GAP"
            elif records < self.DEFAULT_SPARSE_THRESHOLD:
                status = "SPARSE"
            else:
                status = "OK"
            stats.append(
                {
                    "date": d,
                    "records": records,
                    "commodities": commodities,
                    "mandis": mandis,
                    "status": status,
                }
            )
        return stats
