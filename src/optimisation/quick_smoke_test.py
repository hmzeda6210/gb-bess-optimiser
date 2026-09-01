"""Phase 3 quick smoke-test: run the forecast-driven dispatch across a
handful of dates spanning different seasons, before investing in Phase 4's
full backtest infrastructure."""

from src.optimisation.forecast_dispatch import evaluate_forecast_driven_dispatch

# A small spread across seasons, including your known spring weak-spot
TEST_DATES = [
    "2025-08-15",  # summer
    "2025-11-10",  # autumn
    "2026-01-20",  # winter
    "2026-03-15",  # spring (known weak spot)
    "2026-04-20",  # spring
    "2026-06-10",  # early summer
]

CAPACITY, MAX_POWER, ETA_C, ETA_D = 10.0, 5.0, 0.922, 0.922

if __name__ == "__main__":
    print(f"{'Date':<12} {'Believed':>10} {'Real':>10} {'Perfect':>10} {'% captured':>12} {'Checks':>8}")
    for date in TEST_DATES:
        try:
            result = evaluate_forecast_driven_dispatch(date, CAPACITY, MAX_POWER, ETA_C, ETA_D)
            perfect_profit, _ = __import__("src.optimisation.dispatch", fromlist=["run_dispatch"]).run_dispatch(
                __import__("src.optimisation.dispatch", fromlist=["load_day_ahead_prices"]).load_day_ahead_prices(date),
                CAPACITY, MAX_POWER, ETA_C, ETA_D
            )
            pct = (result["real_profit"] / perfect_profit * 100) if perfect_profit > 0 else float("nan")
            print(f"{date:<12} £{result['believed_profit']:>8.2f} £{result['real_profit']:>8.2f} "
                  f"£{perfect_profit:>8.2f} {pct:>10.1f}%  {result['checks']['all_clean']}")
        except Exception as e:
            print(f"{date:<12} FAILED: {e}")