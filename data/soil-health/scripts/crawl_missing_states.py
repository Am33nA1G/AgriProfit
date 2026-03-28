"""
crawl_missing_states.py

Fetches soil-health nutrient data for the 11 states missing from
nutrients_all.parquet, then appends them into that parquet.

Target site : https://soilhealth.dac.gov.in/nutrient-dashboard
Output CSVs : data/soil-health/raw_csvs/<state>_<district>_<block>_<cycle>.csv
Final merge : data/soil-health/nutrients_all.parquet  (appended, deduped)

Usage:
    pip install playwright pandas pyarrow tqdm
    playwright install chromium
    python data/soil-health/scripts/crawl_missing_states.py
"""

import csv
import re
import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

# ── Windows console UTF-8 ─────────────────────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ─────────────────────────────────────────────────────────────────────
SOIL_DIR    = Path(__file__).resolve().parent.parent   # data/soil-health/
CSV_DIR     = SOIL_DIR / "raw_csvs"
PARQUET_OUT = SOIL_DIR / "nutrients_all.parquet"

URL = "https://soilhealth.dac.gov.in/nutrient-dashboard"

# ── Target states (uppercase, as they appear in the site dropdown) ────────────
# These are confirmed absent from nutrients_all.parquet.
MISSING_STATES = {
    "DELHI",
    "ODISHA",
    "PUNJAB",
    "RAJASTHAN",
    "SIKKIM",
    "TAMIL NADU",
    "TELANGANA",
    "TRIPURA",
    "UTTAR PRADESH",
    "UTTARAKHAND",
    "WEST BENGAL",
}

# ── Timing (ms) ───────────────────────────────────────────────────────────────
WAIT_AFTER_SELECT = 1500   # after clicking a dropdown option
WAIT_CARDS        = 4000   # wait for nutrient cards to render
WAIT_FILTER       = 2500   # after clicking the Filter button
MAX_RETRIES       = 3
MAX_DISTRICT_FAILS = 5     # reload if this many consecutive district failures


# ══════════════════════════════════════════════════════════════════════════════
# FILE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def safe_name(text: str) -> str:
    text = re.sub(r'[\\/:*?"<>|&]', "_", text)
    return re.sub(r"\s+", " ", text).strip()


def already_done(csv_dir: Path) -> set:
    """
    Return a set of (cycle, state, district, block) tuples already written to
    CSV.  Reads the first data row of each file — more reliable than filename
    parsing.
    """
    done = set()
    for f in csv_dir.glob("*.csv"):
        try:
            df = pd.read_csv(f, nrows=1)
            if {"cycle", "state", "district", "block"}.issubset(df.columns):
                r = df.iloc[0]
                done.add((str(r["cycle"]), str(r["state"]),
                           str(r["district"]), str(r["block"])))
        except Exception:
            pass
    return done


def write_csv(csv_dir: Path,
              cycle: str, state: str, district: str, block: str,
              rows: list) -> None:
    fname = (
        f"{safe_name(state)}_"
        f"{safe_name(district)}_"
        f"{safe_name(block)}_"
        f"{safe_name(cycle)}.csv"
    )
    out = csv_dir / fname
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cycle", "state", "district", "block",
                    "nutrient", "high", "medium", "low"])
        for r in rows:
            w.writerow([cycle, state, district, block, *r])


# ══════════════════════════════════════════════════════════════════════════════
# PLAYWRIGHT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def open_listbox(page, label_text: str):
    """
    Open the MUI Autocomplete dropdown identified by its <label> text.
    Returns a locator for the <li> options, or None on failure.
    """
    for attempt in range(MAX_RETRIES):
        try:
            label = page.locator("label", has_text=label_text).first
            input_id = label.get_attribute("for")
            inp = page.locator(f"input#{input_id}")
            inp.click(force=True)
            page.keyboard.press("ArrowDown")
            page.wait_for_selector("ul[role='listbox']", timeout=8000)
            return page.locator("ul[role='listbox'] li[role='option']")
        except PwTimeout:
            if attempt < MAX_RETRIES - 1:
                page.wait_for_timeout(1500)
    return None


def list_options(page, label_text: str) -> list:
    opts = open_listbox(page, label_text)
    if opts is None:
        page.keyboard.press("Escape")
        return []
    vals = opts.evaluate_all("els => els.map(e => e.textContent.trim())")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    return vals


def select_option(page, label_text: str, value: str) -> bool:
    opts = open_listbox(page, label_text)
    if opts is None:
        return False
    for i in range(opts.count()):
        try:
            if opts.nth(i).inner_text().strip() == value:
                opts.nth(i).click(force=True)
                page.wait_for_timeout(WAIT_AFTER_SELECT)
                return True
        except Exception:
            pass
    page.keyboard.press("Escape")
    return False


def scrape_nutrient_cards(page) -> list:
    """
    Extract [(nutrient, high_pct, medium_pct, low_pct), ...] from the visible
    MUI cards.  Values are floats (percentage points, sum ≈ 100).
    """
    page.wait_for_timeout(WAIT_CARDS)
    cards = page.locator(".MuiCard-root")
    rows = []
    for i in range(cards.count()):
        c = cards.nth(i)
        try:
            nutrient = c.locator("h6").inner_text().strip()
            nums = []
            for t in c.locator("span").all_inner_texts():
                try:
                    nums.append(float(t.strip().replace("%", "").strip()))
                except ValueError:
                    pass
            if len(nums) >= 3:
                rows.append((nutrient, nums[0], nums[1], nums[2]))
        except Exception:
            pass
    return rows


def reload_dashboard(page):
    page.goto(URL, timeout=60_000)
    page.wait_for_timeout(5000)


# ══════════════════════════════════════════════════════════════════════════════
# CORE CRAWL
# ══════════════════════════════════════════════════════════════════════════════

def crawl(page, csv_dir: Path, done: set) -> None:
    reload_dashboard(page)

    cycles = list_options(page, "Select Cycle")
    if not cycles:
        print("ERROR: Could not read cycles — check if the site is accessible.")
        return
    print(f"Cycles found: {cycles}\n")

    for cycle in cycles:
        print(f"\n{'='*64}")
        print(f"CYCLE: {cycle}")
        print(f"{'='*64}")

        # Hard reset per cycle to avoid stale state
        reload_dashboard(page)

        if not select_option(page, "Select Cycle", cycle):
            print(f"  Could not select cycle '{cycle}', skipping.")
            continue

        page.get_by_role("button", name="Filter").click()
        page.wait_for_timeout(WAIT_FILTER)

        all_states = list_options(page, "Select State")
        targets = [s for s in all_states if s.upper() in MISSING_STATES]
        print(f"  Missing states visible in site: {targets}")

        if not targets:
            print("  None of the target states appear in this cycle.")
            continue

        for state in targets:
            print(f"\n  STATE: {state}")

            if not select_option(page, "Select State", state):
                print(f"    Could not select state '{state}', skipping.")
                continue

            districts = list_options(page, "Select District")
            if not districts:
                print(f"    No districts found for {state}.")
                continue
            print(f"    Districts: {len(districts)}")

            consecutive_fails = 0

            for district in districts:
                if not select_option(page, "Select District", district):
                    print(f"      Could not select district '{district}', skipping.")
                    consecutive_fails += 1
                    if consecutive_fails >= MAX_DISTRICT_FAILS:
                        # State dropdown probably reset — re-select state
                        print(f"    Too many failures — re-selecting state {state}")
                        if not select_option(page, "Select State", state):
                            print(f"    Could not re-select state, moving on.")
                            break
                        consecutive_fails = 0
                    continue

                consecutive_fails = 0

                blocks = list_options(page, "Select Block")
                if not blocks:
                    continue

                saved_count = 0
                for block in blocks:
                    key = (cycle, state, district, block)
                    if key in done:
                        continue

                    if not select_option(page, "Select Block", block):
                        continue

                    rows = scrape_nutrient_cards(page)
                    if not rows:
                        print(f"        No card data for {district}/{block}")
                        continue

                    write_csv(csv_dir, cycle, state, district, block, rows)
                    done.add(key)
                    saved_count += 1

                if saved_count:
                    print(f"      {district}: saved {saved_count} blocks")


# ══════════════════════════════════════════════════════════════════════════════
# MERGE INTO PARQUET
# ══════════════════════════════════════════════════════════════════════════════

def merge_to_parquet(csv_dir: Path, parquet_path: Path) -> None:
    new_files = list(csv_dir.glob("*.csv"))
    if not new_files:
        print("\nNo new CSVs to merge.")
        return

    print(f"\nMerging {len(new_files)} CSV files into parquet…")
    chunks = []
    for f in new_files:
        try:
            df = pd.read_csv(f)
            for col in ["high", "medium", "low"]:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace("%", "", regex=False).str.strip(),
                    errors="coerce",
                )
            chunks.append(df)
        except Exception as e:
            print(f"  Skipped {f.name}: {e}")

    if not chunks:
        print("No valid CSVs loaded.")
        return

    new_df = pd.concat(chunks, ignore_index=True)

    if parquet_path.exists():
        existing = pd.read_parquet(parquet_path)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(
            subset=["cycle", "state", "district", "block", "nutrient"],
            keep="last",
        )
    else:
        combined = new_df

    combined.to_parquet(parquet_path, index=False)

    print(f"\n✅ nutrients_all.parquet updated")
    print(f"   Total rows : {len(combined):,}")
    print(f"   States     : {combined['state'].nunique()} — {sorted(combined['state'].unique())}")
    print(f"   Districts  : {combined['district'].nunique():,}")
    print(f"   Blocks     : {combined['block'].nunique():,}")
    print(f"   Written to : {parquet_path}")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    done = already_done(CSV_DIR)
    print(f"Resume check: {len(done)} blocks already saved in {CSV_DIR}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=80)
        page = browser.new_page()
        try:
            crawl(page, CSV_DIR, done)
        except KeyboardInterrupt:
            print("\nInterrupted — all progress already saved to CSV files.")
        finally:
            browser.close()

    merge_to_parquet(CSV_DIR, PARQUET_OUT)


if __name__ == "__main__":
    main()
