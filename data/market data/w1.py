from pathlib import Path
print(len(list(Path("daily_prices_csv").glob("*.csv"))))
   
   