"""Adapters: the ONLY module that imports from your real src/ system.
Everything downstream (layout, callbacks, components) talks to this
module, never to src/ directly - keeps the UI decoupled from the engine.
"""

import json
import os
from datetime import datetime

from src.optimisation.dispatch import load_day_ahead_prices, run_dispatch, check_schedule
from src.backtesting.metrics import compute_backtest_metrics, compute_seasonal_breakdown

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CAPACITY_MWH = 10.0
MAX_POWER_MW = 5.0
ETA_C = 0.922
ETA_D = 0.922
CAPITAL_BASE_GBP = 3_000_000

# Cost sensitivity: precomputed via scripts/check_costs.py and
# scripts/apply_halved_costs.py, NOT recomputed live on each page load
# (would require re-running the full backtest 3x per view). Update these
# manually if you rerun those scripts with different assumptions.
COST_SENSITIVITY = [
    {"scenario": "No trade costs", "total_profit": 117114, "per_mw_year": 20453, "days_profitable": "342 / 418 (82%)"},
    {"scenario": "Half of assumed costs", "total_profit": 42880, "per_mw_year": 7489, "days_profitable": "235 / 418 (56%)"},
    {"scenario": "Full assumed costs", "total_profit": -31354, "per_mw_year": -5476, "days_profitable": "135 / 418 (32%)"},
]


def get_dispatch_for_date(date_str: str) -> dict:
    prices = load_day_ahead_prices(date_str)
    profit, schedule = run_dispatch(prices, CAPACITY_MWH, MAX_POWER_MW, ETA_C, ETA_D)
    checks = check_schedule(schedule, CAPACITY_MWH, MAX_POWER_MW, ETA_C, ETA_D)
    return {"date": date_str, "profit": profit, "schedule": schedule, "checks": checks}


def get_backtest_results(path: str = None) -> list:
    path = path or os.path.join(BASE_DIR, "backtest_results.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_backtest_metrics(results: list) -> dict:
    return compute_backtest_metrics(results, MAX_POWER_MW, CAPITAL_BASE_GBP)


def get_seasonal_breakdown(results: list) -> dict:
    return compute_seasonal_breakdown(results)


def get_equity_curve(results: list, capital_base: float = CAPITAL_BASE_GBP) -> dict:
    """Computed LIVE from backtest_results.json - real daily granularity,
    not the coarser monthly aggregation used elsewhere for display size."""
    dates, before, after = [], [], []
    running_before, running_after = capital_base, capital_base
    has_after_costs = results and "real_profit_after_costs" in results[0]

    for r in sorted(results, key=lambda x: x["date"]):
        running_before += r["real_profit"]
        before.append(running_before)
        dates.append(r["date"])
        if has_after_costs:
            running_after += r["real_profit_after_costs"]
            after.append(running_after)

    return {"dates": dates, "before_costs": before, "after_costs": after if has_after_costs else None}


def get_findings_markdown(path: str = None) -> str:
    path = path or os.path.join(BASE_DIR, "model_finding.md")
    if not os.path.exists(path):
        return "*model_finding.md not found.*"
    with open(path, encoding="utf-8") as f:
        return f.read()


def data_last_updated(path: str = "backtest_results.json") -> str:
    if not os.path.exists(path):
        return "unavailable"
    return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
