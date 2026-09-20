"""Precomputes the MILP dispatch for every backfilled date, ONCE, on your
own machine (fast). The hosted dashboard then looks up results instead of
re-solving the MILP on every click - since these are historical, deterministic
dates, the result is identical to solving live, just much faster to serve.

Run this locally whenever your backfilled date range changes:
    python scripts/precompute_dispatch.py
Then commit the resulting dispatch_cache.json and push - the hosted app
will pick it up on its next `git pull` + Reload.
"""

import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.optimisation.dispatch import load_day_ahead_prices, run_dispatch, check_schedule

CAPACITY_MWH = 10.0
MAX_POWER_MW = 5.0
ETA_C = 0.922
ETA_D = 0.922

START_DATE = "2025-05-01"
END_DATE = "2026-07-23"


def precompute():
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end = datetime.strptime(END_DATE, "%Y-%m-%d")

    cache = {}
    current = start
    total_days = (end - start).days + 1
    i = 0

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        i += 1
        try:
            prices = load_day_ahead_prices(date_str)
            profit, schedule = run_dispatch(prices, CAPACITY_MWH, MAX_POWER_MW, ETA_C, ETA_D)
            checks = check_schedule(schedule, CAPACITY_MWH, MAX_POWER_MW, ETA_C, ETA_D)
            cache[date_str] = {"date": date_str, "profit": profit, "schedule": schedule, "checks": checks}
        except Exception as e:
            print(f"{date_str}: SKIPPED ({e})")

        if i % 50 == 0 or i == total_days:
            print(f"Progress: {i}/{total_days}")

        current += timedelta(days=1)

    with open("dispatch_cache.json", "w") as f:
        json.dump(cache, f)

    print(f"\nDone. Cached {len(cache)} dates to dispatch_cache.json")


if __name__ == "__main__":
    precompute()