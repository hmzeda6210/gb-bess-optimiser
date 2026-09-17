"""One-off test: proves ingest_yesterday() actually triggers the retry/cutoff
path and returns gracefully when data is genuinely unavailable - using the
REAL function, real network calls, just with shortened delays for testing."""

import sys
sys.path.insert(0, ".")

import src.deployment.run_daily as run_daily_module

run_daily_module.RETRY_DELAYS_SECONDS = [3, 3]
run_daily_module.MAX_INGESTION_WAIT_SECONDS = 15

FUTURE_DATE = "2030-01-01"

print(f"Testing ingestion cutoff against {FUTURE_DATE} (expected: no data available)...")
complete = run_daily_module.ingest_yesterday(FUTURE_DATE)
print(f"\nResult: complete={complete}")
print("Expected: complete=False, with a 'cutoff reached' warning logged above, "
      "and the function returning promptly rather than hanging.")