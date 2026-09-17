"""Compact key-metrics row. Only shows figures your system actually
produces - no invented confidence scores or fabricated KPIs."""

from dash import html


def metric_card(label: str, value: str, sentiment: str = "") -> html.Div:
    return html.Div(
        [
            html.Div(label, className="metric-label"),
            html.Div(value, className=f"metric-value {sentiment}".strip()),
        ],
        className="metric-card",
    )


def build_metrics_row(metrics: dict) -> html.Div:
    sentiment = "positive" if metrics["total_real_profit"] >= 0 else "negative"
    return html.Div(
        [
            metric_card("Total Profit", f"£{metrics['total_real_profit']:,.0f}", sentiment),
            metric_card("Capture Rate", f"{metrics['capture_rate']:.1%}"),
            metric_card("£/MW/Year", f"£{metrics['profit_per_mw_per_year']:,.0f}"),
            metric_card("Max Drawdown", f"£{metrics['max_drawdown_gbp']:,.0f}", "negative"),
        ],
        className="metrics-row",
    )
