import pandas as pd
from pathlib import Path
from tqdm import tqdm

# ================= CONFIG =================

CSV_DIR = Path(r"D:\soil-health-data\nutrients")
OUT_PARQUET = Path(r"D:\soil-health-data\nutrients_all.parquet")

# ================= MAIN =================

def main():
    files = list(CSV_DIR.glob("*.csv"))
    if not files:
        print("❌ No CSV files found")
        return

    print(f"Found {len(files)} CSV files")

    chunks = []

    for f in tqdm(files, desc="Reading CSVs"):
        try:
            df = pd.read_csv(f)

            # Basic sanity
            required = {
                "cycle", "state", "district", "block",
                "nutrient", "high", "medium", "low"
            }
            if not required.issubset(df.columns):
                continue

            # Normalize
            df["cycle"] = df["cycle"].astype(str)
            df["state"] = df["state"].str.strip()
            df["district"] = df["district"].str.strip()
            df["block"] = df["block"].str.strip()
            df["nutrient"] = df["nutrient"].str.strip()

            # Convert numbers safely
            for c in ["high", "medium", "low"]:
                df[c] = (
                    df[c]
                    .astype(str)
                    .str.replace("%", "", regex=False)
                    .str.strip()
                    .astype(float)
                )

            chunks.append(df)

        except Exception as e:
            print(f"⚠️ Skipped {f.name}: {e}")

    if not chunks:
        print("❌ No valid data loaded")
        return

    full = pd.concat(chunks, ignore_index=True)

    print("\n=== FINAL DATASET ===")
    print("Rows     :", len(full))
    print("Cycles   :", full['cycle'].nunique())
    print("States   :", full['state'].nunique())
    print("Districts:", full['district'].nunique())
    print("Blocks   :", full['block'].nunique())
    print("Nutrients:", full['nutrient'].nunique())

    full.to_parquet(OUT_PARQUET, index=False)
    print(f"\n✅ Parquet written to: {OUT_PARQUET}")


if __name__ == "__main__":
    main()
