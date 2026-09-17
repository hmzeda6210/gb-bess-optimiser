"""Performance page - equity curve, seasonality, cost sensitivity, findings."""

from dash import html, dcc

from data.adapters import (
    get_backtest_results, get_backtest_metrics, get_seasonal_breakdown,
    get_equity_curve, get_findings_markdown, COST_SENSITIVITY,
)
from components.performance_charts import build_equity_curve_chart, build_seasonality_chart, build_year_month_heatmap
from components.cost_table import build_cost_sensitivity_table


def build_performance_layout():
    results = get_backtest_results()
    metrics = get_backtest_metrics(results)
    seasonal = get_seasonal_breakdown(results)
    equity = get_equity_curve(results)
    findings_md = get_findings_markdown()

    return html.Div(
        [
            html.Div(
                [
                    html.H1("Performance"),
                    html.Div(f"Walk-forward backtest — {metrics['n_days']} days", className="subtitle"),
                ],
                className="page-header",
            ),

            html.Div(
                [
                    html.H2("Equity curve"),
                    dcc.Graph(figure=build_equity_curve_chart(equity), config={"displayModeBar": False}),
                ],
                className="section",
            ),

            html.Div(
                [
                    html.H2("Seasonality"),
                    dcc.Graph(figure=build_seasonality_chart(seasonal), config={"displayModeBar": False}),
                ],
                className="section",
            ),

            html.Div(
                [
                    html.H2("Year-over-year seasonality"),
                    html.Div(
                        "Same calendar month, split by year — shows whether a month's "
                        "profile is stable or shifted between 2025 and 2026.",
                        className="chart-note",
                    ),
                    dcc.Graph(figure=build_year_month_heatmap(results), config={"displayModeBar": False}),
                ],
                className="section",
            ),

            html.Div(
                [
                    html.H2("Cost sensitivity"),
                    build_cost_sensitivity_table(COST_SENSITIVITY),
                ],
                className="section",
            ),

            html.Div(
                [
                    html.H2("Findings and limitations"),
                    dcc.Markdown(findings_md, className="findings-md"),
                ],
                className="section",
            ),
        ],
        className="page",
    )
