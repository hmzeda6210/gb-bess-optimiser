"""Phase 4: aggregate metrics computed from a walk-forward backtester's
daily results. Deliberately refuses to report Sharpe with too few days
rather than output a misleading number."""

import numpy as np


def compute_backtest_metrics(daily_results: list, max_power_mw: float,
                              capital_base_gbp: float = None) -> dict:
    real = np.array([d["real_profit"] for d in daily_results])
    perfect = np.array([d["perfect_profit"] for d in daily_results])
    n_days = len(daily_results)

    capture_rate = real.sum() / perfect.sum() if perfect.sum() != 0 else float("nan")

    if n_days < 30 or real.std() == 0:
        sharpe_annualised = None
        sharpe_note = f"unreliable with n_days={n_days} < 30, not reported"
    else:
        sharpe_daily = real.mean() / real.std()
        sharpe_annualised = sharpe_daily * np.sqrt(252)
        sharpe_note = ("Sharpe is scale-invariant to £ vs % return - reported value is "
                        "identical either way. Likely overstated: retrain_every creates "
                        "correlated (non-independent) daily returns within each retrain "
                        "window, and the standard sqrt(252) annualisation assumes "
                        "independence - a known limitation, not yet corrected for.")

    cumulative = np.cumsum(real)
    running_max = np.maximum.accumulate(cumulative)
    max_drawdown_gbp = (cumulative - running_max).min()

    profit_per_mw_per_day = real.sum() / max_power_mw / n_days
    profit_per_mw_per_year = profit_per_mw_per_day * 365

    failing_days = [d["date"] for d in daily_results if not d.get("checks_clean", True)]

    result = {
        "n_days": n_days,
        "total_real_profit": real.sum(),
        "total_perfect_profit": perfect.sum(),
        "capture_rate": capture_rate,
        "sharpe_annualised": sharpe_annualised,
        "sharpe_note": sharpe_note,
        "max_drawdown_gbp": max_drawdown_gbp,
        "profit_per_mw_per_year": profit_per_mw_per_year,
        "failing_days": failing_days,
    }

    if capital_base_gbp:
        # Real equity curve: capital base plus cumulative profit, tracked day by day
        equity_curve = capital_base_gbp + cumulative
        running_max_equity = np.maximum.accumulate(equity_curve)
        drawdown_pct = (equity_curve - running_max_equity) / running_max_equity * 100
        max_drawdown_pct = drawdown_pct.min()

        annual_return_pct = (real.mean() / capital_base_gbp) * 252 * 100

        result["capital_base_gbp"] = capital_base_gbp
        result["annual_return_pct"] = annual_return_pct
        result["max_drawdown_pct"] = max_drawdown_pct
        
    if daily_results and "real_profit_after_costs" in daily_results[0]:
        after_costs = np.array([d["real_profit_after_costs"] for d in daily_results])
        result["total_real_profit_after_costs"] = after_costs.sum()
        result["profit_per_mw_per_year_after_costs"] = (after_costs.sum() / max_power_mw / n_days) * 365
     

    return result

def compute_seasonal_breakdown(daily_results: list) -> dict:
    """Win rate and average win/loss size, grouped by month - turns the
    spring weak-spot finding into a quantified, per-month statistic."""
    from collections import defaultdict

    by_month = defaultdict(list)
    for d in daily_results:
        by_month[d["month"]].append(d["real_profit"])

    breakdown = {}
    for month, profits in sorted(by_month.items()):
        profits = np.array(profits)
        wins = profits[profits > 0]
        losses = profits[profits < 0]
        breakdown[month] = {
            "n_days": len(profits),
            "win_rate": len(wins) / len(profits) if len(profits) > 0 else float("nan"),
            "avg_win": wins.mean() if len(wins) > 0 else 0.0,
            "avg_loss": losses.mean() if len(losses) > 0 else 0.0,
            "total_profit": profits.sum(),
            "profit_per_day" : profits.mean(),
        }
    return breakdown