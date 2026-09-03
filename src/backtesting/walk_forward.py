"""Phase 4: causal walk-forward backtester with periodic retraining."""

import time
import json
from datetime import datetime, timedelta

from src.analysis.feature_matrix import build_features
from src.optimisation.forecast_dispatch import train_p50_model, forecast_with_model
from src.optimisation.dispatch import load_day_ahead_prices, run_dispatch, check_schedule
from src.backtesting.metrics import compute_backtest_metrics, compute_seasonal_breakdown
from src.backtesting.costs import compute_trade_costs


class WalkForwardBacktester:
    def __init__(self, start_date: str, end_date: str, capacity: float, max_power: float,
                 eta_c: float, eta_d: float, retrain_every: int = 30):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.capacity = capacity
        self.max_power = max_power
        self.eta_c = eta_c
        self.eta_d = eta_d
        self.retrain_every = retrain_every
        self.daily_results = []

    def _test_days(self):
        d = self.start_date
        while d <= self.end_date:
            yield d
            d += timedelta(days=1)

    def run(self):
        df = build_features("gb_day_ahead_price")
        model = None
        total_days = (self.end_date - self.start_date).days + 1
        start_time = time.time()

        for i, test_day in enumerate(self._test_days()):
            date_str = test_day.strftime("%Y-%m-%d")

            if i % self.retrain_every == 0:
                model = train_p50_model(df, date_str)

            try:
                forecast_prices = forecast_with_model(df, model, date_str)
                actual_prices = load_day_ahead_prices(date_str)

                common_periods = set(forecast_prices) & set(actual_prices)
                forecast_mae = sum(abs(forecast_prices[p] - actual_prices[p]) for p in common_periods) / len(common_periods) if common_periods else None

                believed_profit, schedule = run_dispatch(
                    forecast_prices, self.capacity, self.max_power, self.eta_c, self.eta_d
                )
                real_profit = sum(
                    actual_prices[r["period"]] * (r["discharge"] - r["charge"])
                    for r in schedule if r["period"] in actual_prices
                )

                costs = compute_trade_costs(schedule)
                real_profit_after_costs = real_profit - costs["total_cost"]

                perfect_profit, _ = run_dispatch(
                    actual_prices, self.capacity, self.max_power, self.eta_c, self.eta_d
                )
                checks = check_schedule(schedule, self.capacity, self.max_power, self.eta_c, self.eta_d)

                self.daily_results.append({
                    "date": date_str,
                    "month": test_day.month,
                    "retrained": i % self.retrain_every == 0,
                    "believed_profit": believed_profit,
                    "real_profit": real_profit,
                    "real_profit_after_costs": real_profit_after_costs,
                    "trade_cost": costs["total_cost"],
                    "perfect_profit": perfect_profit,
                    "forecast_mae": forecast_mae,
                    "checks_clean": checks["all_clean"],
                })
            except Exception as e:
                print(f"{date_str}: SKIPPED ({e})")

            if (i + 1) % 20 == 0 or (i + 1) == total_days:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                remaining = (total_days - (i + 1)) / rate if rate > 0 else 0
                print(f"--- Progress: {i+1}/{total_days} days ({elapsed:.0f}s elapsed, "
                      f"~{remaining:.0f}s remaining) ---")

        return self.daily_results
    
def save_results(daily_results: list, filepath: str = "backtest_results.json"):
    with open(filepath, "w") as f:
        json.dump(daily_results, f)
    print(f"Saved results to {filepath}")
    
def load_results(filepath: str = "backtest_results.json") -> list:
    with open(filepath) as f:
        return json.load(f)
        

if __name__ == "__main__":
    bt = WalkForwardBacktester(
        "2025-06-01", "2026-07-23",
        capacity=10.0, max_power=5.0, eta_c=0.922, eta_d=0.922,
        retrain_every=30
    )
    results = bt.run()
    save_results(results)
    print(f"\nTotal days: {len(results)}, retrains: {sum(r['retrained'] for r in results)}")

    CAPITAL_BASE = 3_000_000
    metrics = compute_backtest_metrics(results, max_power_mw=5.0, capital_base_gbp=CAPITAL_BASE)
    print("\n--- Backtest metrics ---")
    for k, v in metrics.items():
        print(f"{k}: {v}")

    seasonal = compute_seasonal_breakdown(results)
    print("\n--- Seasonal breakdown ---")
    for month, stats in seasonal.items():
        print(f"Month {month:2d}: n={stats['n_days']:3d}  win_rate={stats['win_rate']:.1%}  "
              f"avg_win=£{stats['avg_win']:.2f}  avg_loss=£{stats['avg_loss']:.2f}  "
              f"profit/day=£{stats['profit_per_day']:.2f}  total=£{stats['total_profit']:.2f}")
