"""Renders the diagnostics dict from derive_diagnostics() as a panel.
Fields that came back None are shown as 'n/a' explicitly, never omitted
silently - the panel should never imply certainty it doesn't have."""

from dash import html


def _row(label: str, value) -> html.Div:
    display = "n/a" if value is None else value
    return html.Div(
        [html.Span(label, className="diag-label"), html.Span(str(display), className="diag-value")],
        className="diag-row",
    )


def build_diagnostics_panel(diag: dict) -> html.Div:
    if diag is None:
        return html.Div("Select a dispatch period to see the optimiser's reasoning.",
                         className="diag-placeholder")

    header = html.Div(
        [
            html.Span(f"Period {diag['period']}", className="diag-period"),
            html.Span(diag["action"], className=f"diag-action diag-action-{diag['action'].lower()}"),
        ],
        className="diag-header",
    )

    rows = [
        _row("Market price", f"£{diag['price']:.2f}/MWh"),
        _row("SoC before", f"{diag['soc_before']:.2f} MWh"),
        _row("SoC after", f"{diag['soc_after']:.2f} MWh"),
        _row("Binding constraint", diag["binding_constraint"]),
    ]

    if diag["action"] == "DISCHARGE":
        rows.append(_row("Previous charge price",
                          f"£{diag['previous_charge_price']:.2f}/MWh" if diag["previous_charge_price"] else None))
        rows.append(_row("Spread vs. last charge",
                          f"£{diag['spread_vs_last_charge']:.2f}/MWh" if diag["spread_vs_last_charge"] else None))

    rows.append(_row("Round-trip efficiency", f"{diag['round_trip_efficiency']:.1%}"))

    return html.Div([header] + rows, className="diag-panel")
