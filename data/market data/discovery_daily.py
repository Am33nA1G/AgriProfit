import json
import time
import requests
from datetime import date

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

with open("metadata/commodities_1.json") as f:
    commodities = json.load(f)["data"]

with open("metadata/states.json") as f:
    states = json.load(f)["data"]

session = requests.Session()
session.headers.update(HEADERS)

valid_pairs = []

print("Starting discovery...\n")

for com in commodities:
    for st in states:
        payload = {
            "commodity_id": com["commodity_id"],
            "state_id": st["census_state_id"],
            "district_id": 0,
            "calculation_type": "d",
            "start_date": START_DATE,
            "end_date": END_DATE
        }

        r = session.post(API, json=payload, timeout=30)
        rows = r.json().get("data", [])

        if rows:
            print(f"✔ {com['commodity_disp_name']} | {st['census_state_name']}")
            valid_pairs.append({
                "commodity_id": com["commodity_id"],
                "commodity_name": com["commodity_disp_name"],
                "state_id": st["census_state_id"],
                "state_name": st["census_state_name"]
            })

        time.sleep(0.3)

with open("valid_pairs.json", "w") as f:
    json.dump(valid_pairs, f, indent=2)

print(f"\nDiscovery complete. Valid pairs: {len(valid_pairs)}")
