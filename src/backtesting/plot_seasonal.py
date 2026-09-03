"""Phase 4: visualize backtest performance — seasonal patterns, equity
curve, rolling capture rate, forecast-error correlation, and a combined
tearsheet summary."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.backtesting.walk_forward import load_results
from src.backtesting.metrics import compute_backtest_metrics, compute_seasonal_breakdown

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def plot_seasonal_profit(seasonal: dict, filename="seasonal_profit_per_day.png"):
    months = sorted(seasonal.keys())
    profit_per_day = [seasonal[m]["profit_per_day"] for m in months]
    win_rate = [seasonal[m]["win_rate"] * 100 for m in months]
    labels = [MONTH_NAMES[m - 1] for m in months]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    ax1.bar(labels, profit_per_day, color="tab:blue")
    ax1.set_ylabel("£/day")
    ax1.set_title("Average daily profit by calendar month")
    ax1.grid(axis="y", alpha=0.3)

    ax2.bar(labels, win_rate, color="tab:green")
    ax2.set_ylabel("% of days profitable")
    ax2.set_title("Win rate by calendar month")
    ax2.set_ylim(0, 100)
    ax2.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(filename)
    print(f"Saved {filename}")


def plot_equity_curve(daily_results: list, capital_base_gbp: float, filename="equity_curve.png"):
    dates = pd.to_datetime([d["date"] for d in daily_results])
    real = np.array([d["real_profit"] for d in daily_results])
    cumulative = np.cumsum(real)
    equity = capital_base_gbp + cumulative
    running_max = np.maximum.accumulate(equity)
    drawdown = equity - running_max

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                                     gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(dates, equity, color="tab:blue", label="Equity")
    ax1.plot(dates, running_max, color="gray", linestyle="--", linewidth=1, label="Running peak")
    ax1.set_ylabel("£")
    ax1.set_title("Equity curve")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.fill_between(dates, drawdown, 0, color="tab:red", alpha=0.4)
    ax2.set_ylabel("£ drawdown")
    ax2.set_title("Drawdown from running peak")
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(filename)
    print(f"Saved {filename}")


def plot_rolling_capture_rate(daily_results: list, window: int = 30, filename="rolling_capture.png"):
    df = pd.DataFrame(daily_results)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    rolling_real = df["real_profit"].rolling(window).sum()
    rolling_perfect = df["perfect_profit"].rolling(window).sum()
    rolling_capture = rolling_real / rolling_perfect * 100

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df["date"], rolling_capture, color="tab:purple")
    ax.axhline(rolling_capture.mean(), color="gray", linestyle="--", linewidth=1,
               label=f"Mean: {rolling_capture.mean():.1f}%")
    ax.set_ylabel("% of perfect foresight")
    ax.set_title(f"{window}-day rolling capture rate")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(filename)
    print(f"Saved {filename}")


def plot_forecast_error_vs_profit(daily_results: list, filename="error_vs_profit.png"):
    df = pd.DataFrame(daily_results).dropna(subset=["forecast_mae"])
    corr = df["forecast_mae"].corr(df["real_profit"])

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["forecast_mae"], df["real_profit"], alpha=0.5, s=20)
    z = np.polyfit(df["forecast_mae"], df["real_profit"], 1)
    x_line = np.linspace(df["forecast_mae"].min(), df["forecast_mae"].max(), 50)
    ax.plot(x_line, np.polyval(z, x_line), color="red", linewidth=2)
    ax.set_xlabel("Daily forecast MAE (£/MWh)")
    ax.set_ylabel("Real profit (£)")
    ax.set_title(f"Forecast error vs profit (correlation: {corr:.3f})")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(filename)
    print(f"Saved {filename}, correlation={corr:.3f}")


def plot_monthly_heatmap(daily_results: list, filename="monthly_heatmap.png"):
    df = pd.DataFrame(daily_results)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    pivot = df.pivot_table(values="real_profit", index="year", columns="month", aggfunc="mean")

    fig, ax = plt.subplots(figsize=(12, max(2, len(pivot) * 1.2)))
    im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([MONTH_NAMES[m - 1] for m in pivot.columns])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"£{val:.0f}", ha="center", va="center", fontsize=8)
    plt.colorbar(im, ax=ax, label="Avg £/day")
    ax.set_title("Monthly average daily profit")
    fig.tight_layout()
    fig.savefig(filename)
    print(f"Saved {filename}")


def build_tearsheet(daily_results: list, metrics: dict, capital_base_gbp: float,
                     filename="tearsheet.png"):
    df = pd.DataFrame(daily_results)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    cumulative = df["real_profit"].cumsum()
    equity = capital_base_gbp + cumulative
    running_max = equity.cummax()
    drawdown = equity - running_max

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 2, height_ratios=[2, 1, 1.2])

    ax_equity = fig.add_subplot(gs[0, :])
    ax_equity.plot(df["date"], equity, color="tab:blue")
    ax_equity.plot(df["date"], running_max, color="gray", linestyle="--", linewidth=1)
    ax_equity.set_title("Equity Curve")
    ax_equity.grid(alpha=0.3)

    ax_dd = fig.add_subplot(gs[1, :], sharex=ax_equity)
    ax_dd.fill_between(df["date"], drawdown, 0, color="tab:red", alpha=0.4)
    ax_dd.set_title("Drawdown")
    ax_dd.grid(alpha=0.3)

    ax_monthly = fig.add_subplot(gs[2, 0])
    monthly = df.groupby("month")["real_profit"].mean()
    ax_monthly.bar([MONTH_NAMES[m - 1] for m in monthly.index], monthly.values, color="tab:green")
    ax_monthly.set_title("Avg £/day by month")
    ax_monthly.tick_params(axis="x", rotation=45)

    ax_stats = fig.add_subplot(gs[2, 1])
    ax_stats.axis("off")
    stats_text = (
        f"Total profit: £{metrics['total_real_profit']:,.0f}\n"
        f"Capture rate: {metrics['capture_rate']:.1%}\n"
        f"£/MW/year: £{metrics['profit_per_mw_per_year']:,.0f}\n"
        f"Sharpe (see caveat): {metrics['sharpe_annualised']:.2f}\n"
        f"Max drawdown: £{metrics['max_drawdown_gbp']:,.0f} "
        f"({metrics.get('max_drawdown_pct', float('nan')):.3f}%)\n"
        f"Days tested: {metrics['n_days']}\n"
        f"Profit after costs: £{metrics.get('total_real_profit_after_costs', float('nan')):,.0f}\n"
        f"£/MW/year after costs: £{metrics.get('profit_per_mw_per_year_after_costs', float('nan')):,.0f}"
    )
    ax_stats.text(0.05, 0.95, stats_text, transform=ax_stats.transAxes,
                  fontsize=11, verticalalignment="top", fontfamily="monospace")
    ax_stats.set_title("Summary Stats")

    fig.suptitle("GB Battery Dispatch — Backtest Tearsheet", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(filename, dpi=120)
    print(f"Saved {filename}")
    
def plot_equity_curve_comparison(daily_results: list, capital_base_gbp: float,
                                   filename="equity_curve_comparison.png"):
    dates = pd.to_datetime([d["date"] for d in daily_results])
    real = np.array([d["real_profit"] for d in daily_results])
    after_costs = np.array([d["real_profit_after_costs"] for d in daily_results])

    equity_before = capital_base_gbp + np.cumsum(real)
    equity_after = capital_base_gbp + np.cumsum(after_costs)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, equity_before, color="tab:blue", label="Before trade costs")
    ax.plot(dates, equity_after, color="tab:red", label="After trade costs")
    ax.axhline(capital_base_gbp, color="gray", linestyle=":", linewidth=1, label="Starting capital")
    ax.set_ylabel("£")
    ax.set_title("Equity curve: before vs after trade costs")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(filename)
    print(f"Saved {filename}")


if __name__ == "__main__":
    results = load_results()  # loads the saved JSON - no re-run needed
    seasonal = compute_seasonal_breakdown(results)
    metrics = compute_backtest_metrics(results, max_power_mw=5.0, capital_base_gbp=3_000_000)

    plot_seasonal_profit(seasonal)
    plot_equity_curve(results, capital_base_gbp=3_000_000)
    plot_rolling_capture_rate(results)
    plot_forecast_error_vs_profit(results)
    plot_monthly_heatmap(results)
    build_tearsheet(results, metrics, capital_base_gbp=3_000_000)
    plot_equity_curve_comparison(results, capital_base_gbp=3_000_000)
    