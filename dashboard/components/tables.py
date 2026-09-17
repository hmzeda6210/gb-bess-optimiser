"""Dispatch schedule table. Sortable and filterable, per spec."""

from dash import dash_table


def build_dispatch_table(schedule: list, tol: float = 0.01):
    rows = []
    for r in schedule:
        if r["charge"] > tol:
            action, power, energy = "CHARGE", -r["charge"], r["charge"]
        elif r["discharge"] > tol:
            action, power, energy = "DISCHARGE", r["discharge"], r["discharge"]
        else:
            continue
        rows.append({
            "period": r["period"], "action": action,
            "power_mw": round(power, 2), "price": round(r["price"], 2),
            "energy_mwh": round(energy, 2),
        })

    return dash_table.DataTable(
        id="dispatch-table",
        columns=[
            {"name": "Period", "id": "period"},
            {"name": "Action", "id": "action"},
            {"name": "Power (MW)", "id": "power_mw"},
            {"name": "Price (£/MWh)", "id": "price"},
            {"name": "Energy (MWh)", "id": "energy_mwh"},
        ],
        data=rows,
        row_selectable="single",
        selected_rows=[],
        sort_action="native",
        filter_action="native",
        page_size=15,
        style_as_list_view=True,
        style_cell={"fontFamily": "IBM Plex Mono, monospace", "fontSize": "13px", "padding": "8px 12px"},
        style_header={"fontFamily": "IBM Plex Sans, sans-serif", "fontWeight": "600",
                      "backgroundColor": "#F1EFE8", "borderBottom": "1px solid #D9D3C4"},
        style_filter={"fontFamily": "IBM Plex Sans, sans-serif", "fontSize": "12px"},
        style_data_conditional=[
            {"if": {"filter_query": "{action} = CHARGE"}, "color": "#2E6B4F"},
            {"if": {"filter_query": "{action} = DISCHARGE"}, "color": "#B4491F"},
        ],
    )
