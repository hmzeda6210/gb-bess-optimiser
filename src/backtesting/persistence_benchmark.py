"""Benchmark: dispatch driven by YESTERDAY's prices (no model) vs the LightGBM
forecast, on the same days, same MILP, same costs."""

import json
from datetime import datetime, timedelta
import numpy as np

from src.optimisation.dispatch import load_day_ahead_prices, run_dispatch
from src.backtesting.costs import compute_trade_costs

CAPACITY, MAX_POWER, ETA = 10.0, 5.0, 0.922

results = json.load(open("backtest_results.json"))
rows = []
for x in results:
    day = x["date"]
    yesterday = (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    actual = load_day_ahead_prices(day)
    prev = load_day_ahead_prices(yesterday)
    periods = sorted(set(actual) & set(prev))
    if len(periods) < 46:
        continue

    # the "forecast" is simply yesterday's price for the same settlement period
    forecast = {p: prev[p] for p in periods}
    _, schedule = run_dispatch(forecast, CAPACITY, MAX_POWER, ETA, ETA)

    real = sum(actual[r["period"]] * (r["discharge"] - r["charge"]) for r in schedule)
    priced = [{**r, "price": actual[r["period"]]} for r in schedule]
    cost = compute_trade_costs(priced)["total_cost"]

    # persistence profit/cost, then the model's figures for the same day
    rows.append((real, cost, x["real_profit"], x["trade_cost"], x["perfect_profit"]))

a = np.array(rows)
p_real, p_cost, m_real, m_cost, perfect = a.T
n = len(a)

def line(name, profit):
    print(f"{name:34s} total £{profit.sum():>10,.0f}   £/MW/yr £{profit.sum()/5/n*365:>8,.0f}")

print(f"Days compared: {n}\n")
print("Before costs")
line("  Persistence-driven dispatch", p_real)
line("  LightGBM-driven dispatch", m_real)
print(f"  Perfect foresight                  total £{perfect.sum():>10,.0f}")
print(f"  Capture rate: persistence {p_real.sum()/perfect.sum():.1%}  |  model {m_real.sum()/perfect.sum():.1%}")
print("\nHalf costs")
line("  Persistence", p_real - 0.5 * p_cost)
line("  LightGBM", m_real - 0.5 * m_cost)
print("\nFull costs")
line("  Persistence", p_real - p_cost)
line("  LightGBM", m_real - m_cost)

diff = m_real - p_real
se = diff.std(ddof=1) / np.sqrt(n)
print(f"\nModel minus persistence, per day (before costs): mean £{diff.mean():.2f}, "
      f"t-stat {diff.mean()/se:.2f}, model better on {(diff > 0).sum()}/{n} days")
print("(t-stat is rough: days within a retrain window are not independent)")