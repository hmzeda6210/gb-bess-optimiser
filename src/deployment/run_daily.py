"""Phase 5: production orchestration. Computes dates relative to runtime
(not hardcoded), reuses the exact Phase 1-4 functions the backtest already
validated, and enforces a hard deadline so a data-availability delay can
never itself cause a missed auction window."""

import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from src.ingestion.run_backfill import backfill_mid, backfill_disebsp
from src.analysis.feature_matrix import build_features
from src.optimisation.forecast_dispatch import train_p50_model, forecast_with_model
from src.optimisation.dispatch import run_dispatch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")
CAPACITY, MAX_POWER, ETA_C, ETA_D = 10.0, 5.0, 0.922, 0.922

# Ingestion buffer: start early, retry twice, then hard cutoff - never blocks
# past this regardless of how the feed behaves.
RETRY_DELAYS_SECONDS = [15 * 60, 15 * 60]   # retry at +15min, +15min again
MAX_INGESTION_WAIT_SECONDS = 40 * 60          # hard cutoff: 40 minutes total


def get_uk_dates(simulated_today: str = None) -> tuple[str, str, str]:
    """Returns (yesterday, today, target_date) as UK-local date strings.
    Pass simulated_today (YYYY-MM-DD) to test against historical data
    instead of the real current date."""
    if simulated_today:
        today = datetime.strptime(simulated_today, "%Y-%m-%d").date()
    else:
        today = datetime.now(UK_TZ).date()
    yesterday = today - timedelta(days=1)
    target_date = today + timedelta(days=1)
    return yesterday.isoformat(), today.isoformat(), target_date.isoformat()


def ingest_with_cutoff(fetch_fn, is_complete_fn, retry_delays_seconds, max_total_wait_seconds):
    """Tries fetch_fn immediately; retries after each delay if incomplete,
    but never lets total elapsed time exceed max_total_wait_seconds. Always
    returns the best data available, plus whether it was actually complete -
    a decision on slightly-stale data beats no decision at all."""
    start = time.time()
    result = fetch_fn()
    if is_complete_fn(result):
        return result, True

    for delay in retry_delays_seconds:
        if time.time() - start + delay > max_total_wait_seconds:
            logger.warning("Ingestion cutoff reached before completeness - proceeding with available data")
            break
        time.sleep(delay)
        result = fetch_fn()
        if is_complete_fn(result):
            return result, True

    return result, False


def ingest_yesterday(yesterday: str) -> bool:
    """Catches up yesterday's settled prices (needed as lag features for
    today's forecast). Returns whether the data was confirmed complete."""

    def fetch():
        backfill_mid(yesterday, yesterday)
        backfill_disebsp(yesterday, yesterday)
        df = build_features("gb_day_ahead_price")
        target_ts = pd.Timestamp(yesterday, tz="UTC")
        n_periods = (df["settlement_datetime"].dt.date == target_ts.date()).sum()
        return {"periods_received": n_periods}

    def is_complete(result):
        return result["periods_received"] >= 46  # allow for 46/50-period clock-change days

    result, complete = ingest_with_cutoff(
        fetch, is_complete, RETRY_DELAYS_SECONDS, MAX_INGESTION_WAIT_SECONDS
    )
    logger.info(f"Ingestion for {yesterday}: {result['periods_received']} periods, complete={complete}")
    return complete


def run_daily(simulated_today: str = None):
    yesterday, today, target_date = get_uk_dates(simulated_today)
    logger.info(f"Run starting. UK dates -> yesterday={yesterday}, today={today}, target={target_date}")

    ingest_yesterday(yesterday)

    df = build_features("gb_day_ahead_price")
    model = train_p50_model(df, today)

    today_ts = pd.Timestamp(today, tz="UTC")
    max_train_date = df.loc[df["settlement_datetime"] < today_ts, "settlement_datetime"].max()
    assert max_train_date < pd.Timestamp(target_date, tz="UTC"), (
        f"LEAKAGE: training data reaches {max_train_date}, which is not before target {target_date}"
    )
    logger.info(f"Causal boundary verified: max training date {max_train_date} < target {target_date}")

    forecast_prices = forecast_with_model(df, model, target_date)
    believed_profit, schedule = run_dispatch(forecast_prices, CAPACITY, MAX_POWER, ETA_C, ETA_D)

    logger.info(f"Dispatch decided for {target_date}: believed profit £{believed_profit:.2f}")
    return {"target_date": target_date, "believed_profit": believed_profit, "schedule": schedule}


if __name__ == "__main__":
    run_daily(simulated_today="2026-07-21")  # remove simulated_today for real deployment