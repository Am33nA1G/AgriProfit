import pandas as pd
from pathlib import Path

DATA_DIR = Path(r"D:\soil-health-data\nutrients")
OUT_CSV = Path(r"D:\soil-health-data\coverage_report.csv")

def main():
    files = list(DATA_DIR.glob("*.csv"))
    if not files:
        print("❌ No CSV files found")
        return

    print(f"Found {len(files)} CSV files")

    rows = []
    for f in files:
        try:
            df = pd.read_csv(f)
            if df.empty:
                continue

            cycle = df["cycle"].iloc[0]
            state = df["state"].iloc[0]
            district = df["district"].iloc[0]
            block = df["block"].iloc[0]

            rows.append({
                "cycle": cycle,
                "state": state,
                "district": district,
                "block": block,
                "file": f.name
            })
        except Exception as e:
            print(f"⚠️ Failed reading {f.name}: {e}")

    data = pd.DataFrame(rows)

    print("\n=== OVERALL ===")
    print("Cycles   :", data["cycle"].nunique())
    print("States   :", data["state"].nunique())
    print("Districts:", data["district"].nunique())
    print("Blocks   :", data["block"].nunique())

    print("\n=== BLOCK COVERAGE BY STATE & CYCLE ===")
    summary = (
        data
        .groupby(["cycle", "state"])
        .agg(
            districts=("district", "nunique"),
            blocks=("block", "nunique")
        )
        .reset_index()
        .sort_values(["cycle", "blocks"], ascending=[True, False])
    )

    print(summary)

    summary.to_csv(OUT_CSV, index=False)
    print(f"\n✅ Coverage report saved to: {OUT_CSV}")

    print("\n=== STATES WITH LOW COVERAGE (LIKELY UI ISSUES) ===")
    low = summary[summary["blocks"] < 20]
    if low.empty:
        print("None 🎉")
    else:
        print(low)


if __name__ == "__main__":
    main()
