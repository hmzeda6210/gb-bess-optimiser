"""Phase 1 exploratory analysis: seasonal price shape and distribution comparison."""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

#Load one price series from gb_prices.db by series_id, with a 'month' column added for seasonal grouping
def load_series(series_id: str) -> pd.DataFrame:
    conn = sqlite3.connect("gb_prices.db")
    df = pd.read_sql_query(
        "SELECT settlement_date, settlement_period, settlement_datetime, value "
        "FROM price_series WHERE series_id = ? ORDER BY settlement_datetime",
        conn, params=(series_id,)
    )
    df["settlement_date"] = pd.to_datetime(df["settlement_date"])
    df["month"] = df["settlement_date"].dt.month
    conn.close()
    return df

#Plot average £/MWh by settlement period (1-48), Winter vs Summer, to reveal the daily price shape and how it shifts by season."""
def plot_seasonal_shape(df: pd.DataFrame, title: str, filename: str):
    seasons = {
        "Winter (Dec/Jan/Feb)": [12, 1, 2],
        "Summer (Jun/Jul/Aug)": [6, 7, 8],
    }
    fig, ax = plt.subplots(figsize=(10, 5))
    for label, months in seasons.items():
        subset = df[df["month"].isin(months)]
        avg_by_period = subset.groupby("settlement_period")["value"].mean()
        ax.plot(avg_by_period.index, avg_by_period.values, label=label)

    ax.set_xlabel("Settlement period (1-48)")
    ax.set_ylabel("£/MWh")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.savefig(filename)
    print(f"Saved {filename}")

#Plot overlaid histograms comparing day-ahead vs imbalance price distributions to compare volatility/spread
def plot_distributions(day_ahead: pd.DataFrame, imbalance: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(day_ahead["value"], bins=100, alpha=0.5, label="Day-ahead", density=True)
    ax.hist(imbalance["value"], bins=100, alpha=0.5, label="Imbalance", density=True)
    ax.set_xlabel("£/MWh")
    ax.set_ylabel("Density")
    ax.set_title("Price distribution: day-ahead vs imbalance")
    ax.legend()
    fig.savefig("price_distributions.png")
    print("Saved price_distributions.png")

#Load both series, report row counts, and generate all seasonal-shape and distribution plots
if __name__ == "__main__":
    day_ahead = load_series("gb_day_ahead_price")
    imbalance = load_series("gb_imbalance_price")

    print(f"Day-ahead: {len(day_ahead)} rows")
    print(f"Imbalance: {len(imbalance)} rows")

    plot_seasonal_shape(day_ahead, "Day-ahead price: average shape, Winter vs Summer", "seasonal_shape_day_ahead.png")
    plot_seasonal_shape(imbalance, "Imbalance price: average shape, Winter vs Summer", "seasonal_shape_imbalance.png")
    plot_distributions(day_ahead, imbalance)