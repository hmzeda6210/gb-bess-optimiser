"""Overview page - the page a recruiter sees first. Content rebuilds when
the date picker changes; see callbacks.py for the actual data refresh."""

from dash import html, dcc

from data.adapters import get_backtest_results, get_backtest_metrics, data_last_updated, CAPACITY_MWH, MAX_POWER_MW

DEFAULT_DATE = "2026-07-20"


def build_overview_layout():
    results = get_backtest_results()
    metrics = get_backtest_metrics(results)

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("GB Battery Arbitrage"),
                            html.Div("Day-ahead dispatch, walk-forward backtested", className="subtitle"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Dispatch date", className="date-label"),
                            dcc.DatePickerSingle(
                                id="dispatch-date-picker",
                                date=DEFAULT_DATE,
                                display_format="YYYY-MM-DD",
                                min_date_allowed="2025-05-01",
                                max_date_allowed="2026-07-23",
                            ),
                        ],
                        className="date-picker-wrap",
                    ),
                ],
                className="page-header",
            ),

            build_metrics_row_static(metrics),

            dcc.Loading(
                html.Div(id="overview-content"),
                type="dot", color="#2E6B4F",
            ),

            dcc.Store(id="dispatch-schedule-store"),
            dcc.Store(id="battery-params-store", data={
                "capacity": CAPACITY_MWH, "max_power": MAX_POWER_MW, "eta_c": 0.922, "eta_d": 0.922,
            }),
        ],
        className="page",
    )


def build_metrics_row_static(metrics: dict) -> html.Div:
    from components.metrics import build_metrics_row
    return build_metrics_row(metrics)
