"""Performance page charts: equity curve (real daily data), seasonality,
and a year-over-year monthly heatmap."""

from collections import defaultdict
from datetime import datetime

import plotly.graph_objects as go

ACCENT = "#2E6B4F"
NEGATIVE = "#B4491F"
GRID_COLOR = "#E3E1DA"
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def build_equity_curve_chart(equity: dict) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity["dates"], y=equity["before_costs"], mode="lines",
        line=dict(color=ACCENT, width=1.5), name="Before costs",
    ))
    if equity["after_costs"] is not None:
        fig.add_trace(go.Scatter(
            x=equity["dates"], y=equity["after_costs"], mode="lines",
            line=dict(color=NEGATIVE, width=1.5), name="After costs",
        ))

    fig.update_layout(
        template="plotly_white", height=340,
        margin=dict(l=50, r=20, t=20, b=40),
        legend=dict(orientation="h", y=1.1, x=0),
        xaxis=dict(gridcolor=GRID_COLOR),
        yaxis=dict(title="£", gridcolor=GRID_COLOR),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color="#26272B"),
    )
    return fig


def build_seasonality_chart(seasonal: dict) -> go.Figure:
    months = sorted(seasonal.keys())
    profit_per_day = [seasonal[m]["profit_per_day"] for m in months]
    labels = [MONTH_NAMES[m - 1] for m in months]
    colors = [ACCENT if v >= 0 else NEGATIVE for v in profit_per_day]

    fig = go.Figure(go.Bar(x=labels, y=profit_per_day, marker_color=colors))
    fig.update_layout(
        template="plotly_white", height=300,
        margin=dict(l=50, r=20, t=20, b=40),
        xaxis=dict(gridcolor=GRID_COLOR),
        yaxis=dict(title="£/day", gridcolor=GRID_COLOR),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color="#26272B"),
    )
    return fig


def build_year_month_heatmap(results: list) -> go.Figure:
    """Year x month average daily profit - shows what the merged calendar-
    month bar chart above cannot: whether the same month behaved
    differently across the two years in the dataset."""
    by_year_month = defaultdict(list)
    for r in results:
        d = datetime.strptime(r["date"], "%Y-%m-%d")
        by_year_month[(d.year, d.month)].append(r["real_profit"])

    years = sorted(set(k[0] for k in by_year_month))
    months = list(range(1, 13))

    z, text = [], []
    for y in years:
        row, row_text = [], []
        for m in months:
            vals = by_year_month.get((y, m))
            if vals:
                avg = sum(vals) / len(vals)
                row.append(avg)
                row_text.append(f"£{avg:.0f}")
            else:
                row.append(None)
                row_text.append("")
        z.append(row)
        text.append(row_text)

    fig = go.Figure(go.Heatmap(
        z=z, x=MONTH_NAMES, y=[str(y) for y in years],
        text=text, texttemplate="%{text}",
        colorscale=[[0, "#B4491F"], [0.5, "#F1EFE8"], [1, "#2E6B4F"]],
        showscale=True, colorbar=dict(title="£/day"),
        hovertemplate="%{y} %{x}<br>Avg: %{z:.0f}£/day<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_white", height=220,
        margin=dict(l=50, r=20, t=20, b=30),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color="#26272B"),
    )
    return fig
