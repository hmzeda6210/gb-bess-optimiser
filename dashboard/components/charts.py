"""Price + dispatch chart. Overlays actual/perfect-foresight price against
the MILP's charge/discharge decisions, with a combined hover tooltip
(price, action, SoC, energy) per settlement period."""

import plotly.graph_objects as go

CHARGE_COLOR = "#2E6B4F"
DISCHARGE_COLOR = "#B4491F"
PRICE_COLOR = "#26272B"
GRID_COLOR = "#E3E1DA"


def build_price_dispatch_chart(schedule: list, tol: float = 0.01) -> go.Figure:
    periods = [r["period"] for r in schedule]
    prices = [r["price"] for r in schedule]

    bar_values, bar_colors, customdata = [], [], []
    for r in schedule:
        if r["charge"] > tol:
            action, energy = "CHARGE", r["charge"]
            bar_values.append(r["charge"]); bar_colors.append(CHARGE_COLOR)
        elif r["discharge"] > tol:
            action, energy = "DISCHARGE", r["discharge"]
            bar_values.append(-r["discharge"]); bar_colors.append(DISCHARGE_COLOR)
        else:
            action, energy = "IDLE", 0.0
            bar_values.append(0); bar_colors.append("rgba(0,0,0,0)")
        customdata.append([action, r["soc"], energy])

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=periods, y=bar_values, marker_color=bar_colors, yaxis="y2",
        name="Power (MW)", hoverinfo="skip",  # tooltip lives on the price line below, to avoid a duplicate popup
    ))

    fig.add_trace(go.Scatter(
        x=periods, y=prices, mode="lines", line=dict(color=PRICE_COLOR, width=1.75),
        name="Price (£/MWh)", customdata=customdata,
        hovertemplate=(
            "<b>Period %{x}</b><br>"
            "Price: £%{y:.2f}/MWh<br>"
            "Action: %{customdata[0]}<br>"
            "SoC: %{customdata[1]:.2f} MWh<br>"
            "Energy: %{customdata[2]:.2f} MWh"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        template="plotly_white",
        height=380,
        margin=dict(l=50, r=50, t=20, b=40),
        showlegend=False,
        xaxis=dict(title="Settlement period", gridcolor=GRID_COLOR),
        yaxis=dict(title="£/MWh", gridcolor=GRID_COLOR),
        yaxis2=dict(title="Power (MW, +charge/-discharge)", overlaying="y", side="right",
                     showgrid=False, zeroline=True, zerolinecolor=GRID_COLOR),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color="#26272B"),
    )
    return fig
