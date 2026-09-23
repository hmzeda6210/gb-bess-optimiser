"""CLI: backfill historical MID data into the local database.

Usage:
    python -m src.ingestion.run_backfill 2026-07-20 2026-07-22
"""

import sys
import time
from datetime import datetime, timezone, timedelta

from src.ingestion.elexon_client import fetch_mid, fetch_disebsp
from src.ingestion.transform import transform_mid_response, transform_disebsp_response
from src.ingestion.db import get_engine, insert_rows

#old function(now optimised)
''''def backfill_mid(from_date: str, to_date: str):
    from_time = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    to_time = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    raw = fetch_mid(from_time, to_time)
    rows = transform_mid_response(raw, is_live_pull=False)

    engine = get_engine()
    insert_rows(engine, rows)
    print(f"Inserted {len(rows)} rows for {from_date} to {to_date}.")'''

#Concurrecy method to retrive data
"""MID's endpoint rejects very large date ranges (observed: 400 Bad Request
    on a 14-month window), so pull in smaller chunks and accumulate."""   
def backfill_mid(from_date: str, to_date: str, chunk_days: int = 7):
    from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    engine = get_engine()
    total_rows = 0
    failed_chunks = []
    chunk_start = from_dt
    while chunk_start <= to_dt:
        chunk_end = min(chunk_start + timedelta(days=chunk_days), to_dt + timedelta(days=1))
        try:
            raw = fetch_mid(chunk_start, chunk_end)
            rows = transform_mid_response(raw, is_live_pull=False)
            insert_rows(engine, rows)
            total_rows += len(rows)
            print(f"{chunk_start.date()} to {chunk_end.date()}: {len(rows)} rows")
        except Exception as e:
            print(f"{chunk_start.date()} to {chunk_end.date()}: FAILED ({e})")
            failed_chunks.append((chunk_start.date(), chunk_end.date()))

        chunk_start = chunk_end

    print(f"\nMID: inserted {total_rows} rows total.")
    if failed_chunks:
        print(f"Failed chunks: {failed_chunks}")    
  
#Backfill imbalance prices day-by-day (DISEBSP has no range endpoint), throttled with a 0.2s sleep between calls
def backfill_disebsp(from_date: str, to_date:str):
    from_dt = datetime.strptime(from_date, "%Y-%m-%d")
    to_dt = datetime.strptime(to_date, "%Y-%m-%d")
    
    engine = get_engine()
    failed_dates = []
    total_rows = 0
    
    
    current = from_dt
    while current <= to_dt:
        date_str = current.strftime("%Y-%m-%d")
        try:
            raw = fetch_disebsp(date_str)
            rows = transform_disebsp_response(raw)
            insert_rows(engine, rows)
            total_rows += len(rows)
            print(f"{date_str}: {len(rows)} rows")
        except Exception as e:
            print(f"{date_str}: Failed ({e})")
            failed_dates.append(date_str)
            
        current += timedelta(days=1)
        time.sleep(0.2)
        
    print(f"\nDISEBSP: inserted {total_rows} rows total.")
    if failed_dates:
        print(f"Failed dates ({len(failed_dates)}): {failed_dates}")

#CLI entry point: dispatch to backfill_mid or backfill_disebsp based on the series arg
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python -m src.ingestion.run_backfill YYYY-MM-DD YYYY-MM-DD")
        sys.exit(1)
        
        
    series, from_date, to_date = sys.argv[1],sys.argv[2], sys.argv[3]
    if series == "mid":
        backfill_mid(from_date, to_date)
    elif series == "disebsp":
        backfill_disebsp(from_date, to_date)
    else:
        print(f"Unknown series '{series}' — expected 'mid' or 'disebsp'.")
        sys.exit(1)
    
    
    

    
