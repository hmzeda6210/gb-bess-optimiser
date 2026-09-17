"""Callbacks: date picker -> chart/table/status refresh; table row -> diagnostics panel."""

from dash import Input, Output, State, html, dcc

from data.adapters import get_dispatch_for_date, data_last_updated
from components.charts import build_price_dispatch_chart
from components.tables import build_dispatch_table
from components.diagnostics import derive_diagnostics
from components.diagnostics_view import build_diagnostics_panel


def register_callbacks(app):

    @app.callback(
        Output("overview-content", "children"),
        Output("dispatch-schedule-store", "data"),
        Input("dispatch-date-picker", "date"),
    )
    def update_overview_content(date_str):
        try:
            dispatch = get_dispatch_for_date(date_str)
        except Exception as e:
            error_panel = html.Div(
                [
                    html.Div("No data available for this date.", className="error-title"),
                    html.Div(str(e), className="error-detail"),
                ],
                className="error-box",
            )
            return error_panel, []

        status_ok = dispatch["checks"]["all_clean"]

        content = html.Div(
            [
                html.Div(
                    [
                        html.Div(f"Date: {dispatch['date']}", className="status-item"),
                        html.Div(f"Data updated: {data_last_updated()}", className="status-item"),
                        html.Div(
                            f"Schedule: {'VALID' if status_ok else 'CONSTRAINT VIOLATION'}",
                            className=f"status-item status-{'ok' if status_ok else 'error'}",
                        ),
                    ],
                    className="status-row",
                ),

                html.Div(
                    [
                        html.H2("Price and dispatch"),
                        dcc.Graph(figure=build_price_dispatch_chart(dispatch["schedule"]),
                                  config={"displayModeBar": False}),
                    ],
                    className="section",
                ),

                html.Div(
                    [
                        html.Div(
                            [html.H2("Dispatch schedule"), build_dispatch_table(dispatch["schedule"])],
                            className="col-main",
                        ),
                        html.Div(
                            [html.H2("Why this decision"),
                             html.Div(id="diagnostics-panel", children=build_diagnostics_panel(None))],
                            className="col-side",
                        ),
                    ],
                    className="section split",
                ),
            ]
        )
        return content, dispatch["schedule"]

    @app.callback(
        Output("diagnostics-panel", "children"),
        Input("dispatch-table", "selected_rows"),
        State("dispatch-table", "data"),
        State("dispatch-schedule-store", "data"),
        State("battery-params-store", "data"),
    )
    def update_diagnostics(selected_rows, table_data, schedule, params):
        if not selected_rows or not schedule:
            return build_diagnostics_panel(None)

        period = table_data[selected_rows[0]]["period"]
        diag = derive_diagnostics(
            schedule, period,
            params["capacity"], params["max_power"], params["eta_c"], params["eta_d"],
        )
        return build_diagnostics_panel(diag)
