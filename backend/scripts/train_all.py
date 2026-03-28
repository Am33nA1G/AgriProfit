"""
train_all.py — Unified training orchestrator for all ML models.

Runs price forecast models (v4), yield prediction models, and seasonal JSON
generation in the correct order with configurable parallelism.

Usage:
    cd backend
    python -m scripts.train_all                      # Train everything
    python -m scripts.train_all --price-only         # Only price forecasts
    python -m scripts.train_all --yield-only         # Only yield models
    python -m scripts.train_all --seasonal-only      # Only seasonal JSON
    python -m scripts.train_all --force              # Retrain even if exists
    python -m scripts.train_all --commodity onion    # Single commodity
    python -m scripts.train_all --workers 4          # Parallel workers (price only)
"""
import sys
import argparse
import logging
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_all")


def main():
    parser = argparse.ArgumentParser(description="Unified ML training orchestrator")
    parser.add_argument("--price-only", action="store_true", help="Train only price forecast models")
    parser.add_argument("--yield-only", action="store_true", help="Train only yield prediction models")
    parser.add_argument("--seasonal-only", action="store_true", help="Build only seasonal JSON fallbacks")
    parser.add_argument("--force", action="store_true", help="Retrain all commodities even if already trained")
    parser.add_argument("--commodity", type=str, default=None, help="Train a single commodity (price models only)")
    parser.add_argument("--workers", type=int, default=1, help="Parallel worker count for price models (default: 1)")
    args = parser.parse_args()

    run_price = not args.yield_only and not args.seasonal_only
    run_yield = not args.price_only and not args.seasonal_only
    run_seasonal = not args.price_only and not args.yield_only

    if args.price_only:
        run_price = True
        run_yield = False
        run_seasonal = False
    elif args.yield_only:
        run_price = False
        run_yield = True
        run_seasonal = False
    elif args.seasonal_only:
        run_price = False
        run_yield = False
        run_seasonal = True

    # ── Phase 1: Seasonal JSON (fast, no deps) ────────────────────────────────
    if run_seasonal:
        logger.info("=" * 60)
        logger.info("PHASE: Seasonal Price Calendars (JSON fallbacks)")
        logger.info("=" * 60)
        try:
            from scripts.generate_seasonal_json import main as _seasonal_main
            _seasonal_main()
        except Exception as e:
            logger.error("Seasonal JSON generation failed: %s", e, exc_info=True)

    # ── Phase 2: Price Forecast Models ────────────────────────────────────────
    if run_price:
        logger.info("=" * 60)
        logger.info("PHASE: Price Forecast Models (v4 — XGBoost + Prophet)")
        logger.info("=" * 60)
        try:
            from scripts.train_forecast_v4 import main as _price_main
            successes, failures = _price_main(
                force=args.force,
                commodity=args.commodity,
                workers=args.workers,
            )
            logger.info("Price forecast training: %d succeeded, %d failed", successes, failures)
        except Exception as e:
            logger.error("Price forecast training failed: %s", e, exc_info=True)

    # ── Phase 3: Yield Prediction Models ──────────────────────────────────────
    if run_yield and not args.commodity:
        logger.info("=" * 60)
        logger.info("PHASE: Yield Prediction Models (RandomForest per category)")
        logger.info("=" * 60)
        try:
            from scripts.train_yield_model import main as _yield_main
            _yield_main()
        except Exception as e:
            logger.error("Yield model training failed: %s", e, exc_info=True)
    elif run_yield and args.commodity:
        logger.info("Skipping yield model training (--commodity flag set — yield trains globally)")

    logger.info("All training phases complete.")


if __name__ == "__main__":
    main()
