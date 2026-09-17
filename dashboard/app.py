"""Entry point. Run from the PROJECT ROOT (not from inside dashboard/):

    python -m dashboard.app
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

import dash
from dash import html, dcc, Input, Output

from layout import build_overview_layout
from performance import build_performance_layout
from callbacks import register_callbacks

app = dash.Dash(__name__, title="GB Battery Arbitrage", suppress_callback_exceptions=True)

app.layout = html.Div([
    dcc.Tabs(id="page-tabs", value="overview", children=[
        dcc.Tab(label="Overview", value="overview"),
        dcc.Tab(label="Performance", value="performance"),
    ]),
    html.Div(id="page-content"),
])


@app.callback(Output("page-content", "children"), Input("page-tabs", "value"))
def render_page(tab):
    if tab == "performance":
        return build_performance_layout()
    return build_overview_layout()


register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
