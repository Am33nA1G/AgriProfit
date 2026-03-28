#!/usr/bin/env python
"""
check_forecast_accuracy.py — Weekly forecast accuracy checker.

Finds rows in forecast_accuracy_log where actual_price is still NULL and
the target date has passed, fetches actual market prices from price_history,
computes APE, and prints a summary of live model accuracy.

Run weekly (or daily) via cron or manually:
    python backend/scripts/check_forecast_accuracy.py

Exit codes:
    0 — success
    1 — DB connection error
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

ENGINE = create_engine(str(settings.database_url), echo=False)
Session = sessionmaker(bind=ENGINE)

_ACTUAL_PRICE_QUERY = text("""
    SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ph.modal_price) AS price_modal
    FROM price_history ph
    JOIN mandis m ON ph.mandi_id = m.id
    JOIN commodities c ON ph.commodity_id = c.id
    WHERE LOWER(c.name) LIKE LOWER(:pattern)
      AND LOWER(m.district) = LOWER(:district)
      AND ph.price_date BETWEEN :date_from AND :date_to
      AND ph.modal_price > 0
""")


def _fetch_actual_price(db, commodity: str, district: str, target: date) -> float | None:
    """Return median modal price for commodity/district within ±3 days of target."""
    pattern = f"%{commodity.replace('_', ' ')}%"
    row = db.execute(
        _ACTUAL_PRICE_QUERY,
        {
            "pattern": pattern,
            "district": district,
            "date_from": target - timedelta(days=3),
            "date_to": target + timedelta(days=3),
        },
    ).fetchone()
    if row and row.price_modal is not None:
        return float(row.price_modal)
    return None


def run() -> None:
    db = Session()
    cutoff = date.today() - timedelta(days=1)

    rows = db.execute(
        text("""
            SELECT id, commodity_name, district_name, target_date, predicted_price
            FROM forecast_accuracy_log
            WHERE actual_price IS NULL
              AND target_date <= :cutoff
            ORDER BY target_date
        """),
        {"cutoff": cutoff},
    ).fetchall()

    if not rows:
        print("No pending accuracy checks.")
        db.close()
        return

    print(f"Checking {len(rows)} forecast(s) whose target date has passed...")
    updated = missing = 0

    for row in rows:
        actual = _fetch_actual_price(
            db, row.commodity_name, row.district_name, row.target_date
        )
        if actual is None:
            missing += 1
            continue

        predicted = float(row.predicted_price) if row.predicted_price else None
        ape = abs(actual - predicted) / actual if (predicted is not None and actual > 0) else None

        db.execute(
            text("""
                UPDATE forecast_accuracy_log
                SET actual_price        = :actual,
                    absolute_pct_error  = :ape,
                    checked_at          = :now
                WHERE id = :id
            """),
            {"actual": actual, "ape": ape, "now": datetime.now(timezone.utc), "id": row.id},
        )
        updated += 1

    db.commit()
    print(f"Updated: {updated}  |  No actual data found: {missing}")

    # Per-model accuracy summary
    summary = db.execute(
        text("""
            SELECT
                model_version,
                COUNT(*)                    AS n,
                AVG(absolute_pct_error)     AS mean_ape,
                MIN(absolute_pct_error)     AS min_ape,
                MAX(absolute_pct_error)     AS max_ape
            FROM forecast_accuracy_log
            WHERE actual_price IS NOT NULL
              AND absolute_pct_error IS NOT NULL
            GROUP BY model_version
            ORDER BY model_version
        """)
    ).fetchall()

    if summary:
        print("\n=== Live Forecast Accuracy (all-time) ===")
        for r in summary:
            print(
                f"  {r.model_version:10s}  n={r.n:4d}  "
                f"mean_MAPE={r.mean_ape * 100:5.1f}%  "
                f"min={r.min_ape * 100:4.1f}%  "
                f"max={r.max_ape * 100:5.1f}%"
            )

    db.close()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
