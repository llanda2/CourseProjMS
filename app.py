# === app.py ===
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

from utils import load_data
from callbacks import register_callbacks

# === Initialize Dash App ===
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.config.suppress_callback_exceptions = True
server = app.server

# === Load Data ===
DATA = load_data()

# === App Layout ===
app.layout = dbc.Container([
    dbc.Row(
        dbc.Col(html.H1("Gun Violence and Legislation Dashboard", style={'textAlign': 'center', 'marginTop': '2rem'}))
    ),
    dbc.Row(dbc.Col(dcc.Tabs(id='tabs', value='incidents', children=[
        dcc.Tab(label='Mass Shooting Incidents Map', value='incidents'),
        dcc.Tab(label='Gun Laws & Death Rates Map', value='gunlaws'),
        dcc.Tab(label='Public Opinion Polls', value='opinion'),
        dcc.Tab(label='Supreme Court & 2A Cases', value='scotus')
    ]))),
    dbc.Row(dbc.Col(html.Div(id='controls-container'))),
    dbc.Row(dbc.Col(html.Div(id='visualization-container', children=[
        html.Div(id='incidents-graph'),
        html.Div(id='gunlaws-graph'),
        html.Div(id='opinion-cleaned-graph'),  # NEW: For cleaned opinion data
        html.Div(id='scotus-graph')
    ])))
])

# === Register Callbacks ===
register_callbacks(app, DATA)

# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)
