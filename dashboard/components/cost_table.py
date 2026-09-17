"""Cost sensitivity table - explicitly labeled as precomputed, not live."""

from dash import html


def build_cost_sensitivity_table(rows: list) -> html.Div:
    header = html.Tr([html.Th(h) for h in ["Scenario", "Total profit", "£/MW/year", "Days profitable"]])
    body_rows = []
    for r in rows:
        sentiment = "positive" if r["total_profit"] >= 0 else "negative"
        body_rows.append(html.Tr([
            html.Td(r["scenario"], className="label"),
            html.Td(f"£{r['total_profit']:,}", className=sentiment),
            html.Td(f"£{r['per_mw_year']:,}", className=sentiment),
            html.Td(r["days_profitable"]),
        ]))
    return html.Div(
        [
            html.Table([html.Thead(header), html.Tbody(body_rows)], className="cost-table"),
            html.Div(
                "Precomputed via scripts/check_costs.py — not recomputed live on page load.",
                className="table-note",
            ),
        ]
    )
