import json
from pathlib import Path

with open("valid_pairs.json") as f:
    valid_pairs = json.load(f)

missing = []

for pair in valid_pairs:
    districts_file = f"metadata/districts_{pair['state_id']}.json"
    if not Path(districts_file).exists():
        continue

    with open(districts_file) as f:
        districts = json.load(f)["data"]

    for d in districts:
        fname = f"{pair['commodity_name']}_{pair['state_name']}_{d['census_district_name']}.csv"
        fname = fname.replace(" ", "_")
        path = Path("daily_prices_csv") / fname

        if not path.exists():
            missing.append({
                "commodity": pair["commodity_name"],
                "state": pair["state_name"],
                "district": d["census_district_name"],
                "commodity_id": pair["commodity_id"],
                "state_id": pair["state_id"],
                "district_id": d["census_district_id"],
            })

print(f"Missing entities: {len(missing)}")

with open("missing_entities.json", "w") as f:
    json.dump(missing, f, indent=2)
