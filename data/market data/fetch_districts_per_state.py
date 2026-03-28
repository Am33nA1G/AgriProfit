import json
import requests
from pathlib import Path

API = "https://agmarknet.ceda.ashoka.edu.in/api/districts"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://agmarknet.ceda.ashoka.edu.in/"
}

with open("metadata/states.json") as f:
    states = json.load(f)["data"]

Path("metadata").mkdir(exist_ok=True)

session = requests.Session()
session.headers.update(HEADERS)

for st in states:
    state_id = st["census_state_id"]

    r = session.get(API, params={"state_id": state_id}, timeout=30)
    data = r.json()

    if not data.get("data"):
        continue

    out = f"metadata/districts_{state_id}.json"
    with open(out, "w") as f:
        json.dump(data, f, indent=2)

    print("Saved", out)
