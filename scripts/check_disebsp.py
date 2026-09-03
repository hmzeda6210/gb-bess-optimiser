import sqlite3

conn = sqlite3.connect('gb_prices.db')
query = """
    SELECT settlement_period, settlement_datetime, published_at
    FROM price_series
    WHERE series_id = 'gb_imbalance_price'
    ORDER BY settlement_period
    LIMIT 5
"""
for row in conn.execute(query):
    print(row)