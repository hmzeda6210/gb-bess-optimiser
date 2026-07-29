import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('gb_prices.db')

start = datetime.strptime("2025-05-01", "%Y-%m-%d")
end = datetime.strptime("2026-07-23", "%Y-%m-%d")

existing_dates = set(
    row[0] for row in conn.execute(
        "SELECT DISTINCT settlement_date FROM price_series WHERE series_id = 'gb_imbalance_price'"
    )
)

missing = []
current = start
while current <= end:
    date_str = current.strftime("%Y-%m-%d")
    if date_str not in existing_dates:
        missing.append(date_str)
    current += timedelta(days=1)

print(f"Missing DISEBSP dates: {len(missing)}")
print(missing)