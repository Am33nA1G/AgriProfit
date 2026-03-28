import json
import csv
import time
import re
import requests
from pathlib import Path
from datetime import date, timedelta
from requests.exceptions import ReadTimeout, ConnectionError

# ================= CONFIG =================

API = "https://agmarknet.ceda.ashoka.edu.in/api/prices"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://agmarknet.ceda.ashoka.edu.in",
    "Referer": "https://agmarknet.ceda.ashoka.edu.in/"
}

START_DATE = "2015-01-01"
END_DATE = date.today().strftime("%Y-%m-%d")

TIMEOUT = 60          # seconds
MAX_RETRIES = 3
BASE_SLEEP = 0.4      # politeness delay

# =========================================


def safe_filename(text: str) -> str:
    """Make filenames Windows-safe."""
    text = text.replace(" ", "_")
    return re.sub(r'[\\/:*?"<>|]', "_", text)


def format_eta(seconds):
    if seconds < 0:
        return "estimating…"
    return str(timedelta(seconds=int(seconds)))


# ---------- load valid pairs ----------
with open("valid_pairs.json") as f:
    valid_pairs = json.load(f)

session = requests.Session()
session.headers.update(HEADERS)

Path("daily_prices_csv").mkdir(exist_ok=True)

HEADER = [
    "date",
    "commodity",
    "commodity_id",
    "state",
    "state_id",
    "district",
    "district_id",
    "price_min",
    "price_max",
    "price_modal",
]

# ---------- pre-compute total work ----------
total_tasks = 0
for pair in valid_pairs:
    districts_file = f"metadata/districts_{pair['state_id']}.json"
    if not Path(districts_file).exists():
        continue
    with open(districts_file) as f:
        total_tasks += len(json.load(f)["data"])

completed = 0
start_time = time.time()

print(f"\nTotal districts to process: {total_tasks}\n")

# ================= MAIN LOOP =================

for pair in valid_pairs:
    commodity_id = pair["commodity_id"]
    commodity_name = pair["commodity_name"]
    state_id = pair["state_id"]
    state_name = pair["state_name"]

    districts_file = f"metadata/districts_{state_id}.json"
    if not Path(districts_file).exists():
        print(f"⚠ Missing districts file: {districts_file}")
        continue

    with open(districts_file) as f:
        districts = json.load(f)["data"]

    for dist in districts:
        district_id = dist["census_district_id"]
        district_name = dist["census_district_name"]

        filename = safe_filename(
            f"{commodity_name}_{state_name}_{district_name}.csv"
        )
        csv_file = Path("daily_prices_csv") / filename

        # -------- resume support --------
        if csv_file.exists():
            completed += 1
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            remaining = total_tasks - completed
            eta = remaining / rate if rate > 0 else -1

            print(
                f"⏭ SKIP  {completed}/{total_tasks} "
                f"({completed/total_tasks:.1%}) | ETA {format_eta(eta)}"
            )
            continue

        payload = {
            "commodity_id": commodity_id,
            "state_id": state_id,
            "district_id": district_id,
            "calculation_type": "d",
            "start_date": START_DATE,
            "end_date": END_DATE,
        }

        rows = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = session.post(API, json=payload, timeout=TIMEOUT)
                r.raise_for_status()
                rows = r.json().get("data", [])
                break

            except (ReadTimeout, ConnectionError):
                print(
                    f"⚠ Timeout ({attempt}/{MAX_RETRIES}) → "
                    f"{commodity_name} | {state_name} | {district_name}"
                )
                time.sleep(5 * attempt)

            except Exception as e:
                print(
                    f"❌ Fatal error → "
                    f"{commodity_name} | {state_name} | {district_name} | {e}"
                )
                rows = None
                break

        if rows is None:
            completed += 1
            continue

        if not rows:
            completed += 1
            continue

        # -------- write CSV (atomic overwrite) --------
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
            for row in rows:
                writer.writerow([
                    row["t"],
                    commodity_name,
                    commodity_id,
                    state_name,
                    state_id,
                    district_name,
                    district_id,
                    row["p_min"],
                    row["p_max"],
                    row["p_modal"],
                ])

        completed += 1
        elapsed = time.time() - start_time
        rate = completed / elapsed if elapsed > 0 else 0
        remaining = total_tasks - completed
        eta = remaining / rate if rate > 0 else -1

        print(
            f"✔ SAVED {completed}/{total_tasks} "
            f"({completed/total_tasks:.1%}) | ETA {format_eta(eta)}"
        )

        time.sleep(BASE_SLEEP)

print("\nHARVEST COMPLETE.")
   
   