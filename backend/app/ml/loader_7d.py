"""
Loader for v5 7-day XGBoost direct multi-step models.

Artifacts per commodity (ml/artifacts/v5/):
  {slug}_lgbm_7d.joblib   — dict {1: XGBRegressor, 2: …, 7: XGBRegressor}
  {slug}_7d_meta.json     — training metrics, district encoder, price stats

IMPORTANT: Use `def` FastAPI handlers (not `async def`) when calling these
loaders — joblib.load is blocking disk I/O, runs in FastAPI's threadpool.
"""
import json
import logging
import threading
from pathlib import Path

import joblib
from cachetools import LRUCache

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
V5_DIR = REPO_ROOT / "ml" / "artifacts" / "v5"

_lock = threading.Lock()
# Store 80 commodity model-dicts (each dict holds 7 XGBRegressors)
_model_cache: LRUCache = LRUCache(maxsize=80)
_meta_cache: LRUCache = LRUCache(maxsize=200)


def load_7d_model(slug: str) -> dict | None:
    """Load and cache the 7-horizon model dict for a commodity.

    Returns:
        dict mapping horizon int (1–7) to fitted XGBRegressor,
        or None if no v5 artifact exists for this slug.
    """
    cache_key = f"v5_{slug}"
    with _lock:
        if cache_key in _model_cache:
            return _model_cache[cache_key]

    path = V5_DIR / f"{slug}_lgbm_7d.joblib"
    if not path.exists():
        return None

    models = joblib.load(path)
    with _lock:
        _model_cache[cache_key] = models
    return models


def load_7d_meta(slug: str) -> dict | None:
    """Load and cache JSON metadata for a v5 7-day model.

    Returns:
        Parsed dict, or None if not found.
    """
    with _lock:
        if slug in _meta_cache:
            return _meta_cache[slug]

    path = V5_DIR / f"{slug}_7d_meta.json"
    if not path.exists():
        return None

    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
        with _lock:
            _meta_cache[slug] = meta
        return meta
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load meta for slug=%s path=%s: %s", slug, path.name, e)
        return None


MAPE_THRESHOLD = 0.25  # 25% — above this we don't serve predictions
MIN_TRAIN_ROWS = 100_000  # v5 qualification: ≥100k training rows
MIN_TRAIN_DISTRICTS = 80  # v5 qualification: ≥80 districts


def list_7d_slugs() -> list[str]:
    """Return sorted list of commodity slugs with v5 7-day models available."""
    if not V5_DIR.exists():
        return []
    return sorted(
        p.stem.removesuffix("_7d_meta")
        for p in V5_DIR.glob("*_7d_meta.json")
    )


def _meets_v5_bar(meta: dict) -> bool:
    """Return True if a meta dict passes all v5 qualification criteria:
    MAPE h7 < 25%, ≥100k training rows, ≥80 districts.
    """
    mape = meta.get("test_mape_h7")
    if mape is None or mape >= MAPE_THRESHOLD:
        return False
    if meta.get("n_train_rows", 0) < MIN_TRAIN_ROWS:
        return False
    if meta.get("n_districts", 0) < MIN_TRAIN_DISTRICTS:
        return False
    return True


def list_good_7d_slugs() -> list[str]:
    """Return sorted slugs whose v5 model meets the full qualification bar:
    MAPE h7 < 25%, ≥100k training rows, ≥80 districts.
    """
    good = []
    for slug in list_7d_slugs():
        meta = load_7d_meta(slug)
        if meta is not None and _meets_v5_bar(meta):
            good.append(slug)
    return sorted(good)


def is_good_7d_slug(slug: str) -> bool:
    """Return True if slug has a v5 model that meets the full qualification bar."""
    meta = load_7d_meta(slug)
    return meta is not None and _meets_v5_bar(meta)


MIN_DISTRICT_ROWS = 14  # minimum price records needed to run the model

# Lazily-built index: district_lower → set of good slugs that have data
_district_slug_index: dict[str, set[str]] | None = None
_index_lock = threading.Lock()


def _build_district_index() -> dict[str, set[str]]:
    """Scan all good v5 history parquets and build district → slugs index.

    Uses a per-district 60-day window that mirrors _load_history_prices exactly:
      cutoff = district_max_date - 60 days
    Only districts with ≥MIN_DISTRICT_ROWS in that window are included,
    meaning the dropdown will only show combinations the v5 service can serve.
    """
    import pandas as pd

    good = set(list_good_7d_slugs())
    index: dict[str, set[str]] = {}

    for slug in good:
        path = V5_DIR / f"{slug}_7d_history.parquet"
        if not path.exists():
            continue
        try:
            df = pd.read_parquet(path, columns=["district", "date"])
            df["date"] = pd.to_datetime(df["date"])
            df["district_lower"] = df["district"].str.lower()
            for dist_lower, group in df.groupby("district_lower"):
                # Per-district cutoff: same as _load_history_prices
                cutoff = group["date"].max() - pd.Timedelta(days=60)
                count = int((group["date"] >= cutoff).sum())
                if count >= MIN_DISTRICT_ROWS:
                    index.setdefault(dist_lower, set()).add(slug)
        except Exception as e:
            logger.warning("Index build failed for slug=%s: %s", slug, e)

    return index


def list_slugs_for_district(district: str) -> list[str]:
    """Return good v5 slugs that have enough price history for this district."""
    global _district_slug_index
    with _index_lock:
        if _district_slug_index is None:
            logger.info("Building district→slug index for %d good commodities…", len(list_good_7d_slugs()))
            _district_slug_index = _build_district_index()
            logger.info("Index built: %d districts covered", len(_district_slug_index))

    return sorted(_district_slug_index.get(district.lower(), set()))


def get_model_cache() -> LRUCache:
    """Expose cache for monitoring."""
    return _model_cache


# ---------------------------------------------------------------------------
# District → State map (lazily loaded from main parquet)
# ---------------------------------------------------------------------------

MAIN_PARQUET = REPO_ROOT / "agmarknet_daily_10yr.parquet"

_district_state_map: dict[str, str] | None = None  # district (title-case) → state
_ds_lock = threading.Lock()


def get_district_state_map() -> dict[str, str]:
    """Return {district: state} mapping, lazily loaded from main parquet."""
    global _district_state_map
    with _ds_lock:
        if _district_state_map is not None:
            return _district_state_map

    try:
        import pandas as pd
        df = pd.read_parquet(MAIN_PARQUET, columns=["district", "state"])
        mapping = (
            df.drop_duplicates(subset=["district"])
            .set_index("district")["state"]
            .to_dict()
        )
        with _ds_lock:
            _district_state_map = mapping
        logger.info("Loaded district→state map: %d districts", len(mapping))
        return mapping
    except Exception as e:
        logger.error("Failed to load district→state map: %s", e)
        return {}


def get_states_for_commodity(slug: str) -> list[str]:
    """Return sorted states that have v5 data for this commodity (≥14 rows in last 60 days)."""
    global _district_slug_index
    with _index_lock:
        if _district_slug_index is None:
            _district_slug_index = _build_district_index()

    districts_lower = {d for d, slugs in _district_slug_index.items() if slug in slugs}
    if not districts_lower:
        return []
    ds_map = get_district_state_map()
    states = {ds_map[d] for d in ds_map if d.lower() in districts_lower}
    return sorted(states)


def get_districts_for_commodity_state(slug: str, state: str) -> list[str]:
    """Return sorted districts in *state* with ≥14 rows in last 60 days for *slug*."""
    global _district_slug_index
    with _index_lock:
        if _district_slug_index is None:
            _district_slug_index = _build_district_index()

    districts_lower = {d for d, slugs in _district_slug_index.items() if slug in slugs}
    if not districts_lower:
        return []
    ds_map = get_district_state_map()
    return sorted(
        d for d in ds_map
        if d.lower() in districts_lower and ds_map.get(d, "").lower() == state.lower()
    )
