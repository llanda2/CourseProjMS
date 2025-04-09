import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import os

# === Initialize Dash app ===
app = dash.Dash(__name__, external_stylesheets=["https://cdn.jsdelivr.net/npm/bootswatch@5.3.2/dist/darkly/bootstrap"
                                                ".min.css"])
app.config.suppress_callback_exceptions = True
server = app.server


# === Load and process data ===

# Load mass shootings data
shootings_df = pd.read_csv('mass_shootings_geocoded.csv')

# Clean mass shootings data
def process_shootings(df):
    df = df.copy()
    # Split and clean latitude and longitude from string
    df[['longitude', 'latitude']] = df['latitude'].str.split(',', expand=True)
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

    # Extract year from incident date
    df['Year'] = df["Incident Date"].str.extract(r'(\d{4})')
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')

    # Calculate total victims
    df['Total Victims'] = df["Victims Killed"] + df["Victims Injured"]

    # Create full location string for hover info
    df['Full Location'] = df.apply(
        lambda row: f"{row['Address']}, {row['City Or County']}, {row['State']}, USA", axis=1
    )

    # Drop rows with missing coordinates
    df = df.dropna(subset=['latitude', 'longitude'])

    return df

processed_shootings = process_shootings(shootings_df)

# Determine year range for slider
min_year = int(processed_shootings['Year'].min())
max_year = int(processed_shootings['Year'].max())

# Load gun laws data
gun_laws_df = pd.read_csv('data/stateLaws.csv')

# Clean gun laws data
gun_laws_df.rename(columns={
    'Label': 'State',
    'Strength of Gun Laws (out of 100 points)': 'Law Strength',
    'Gun Deaths per 100,000 Residents': 'Gun Deaths'
}, inplace=True)

# === App layout ===
app.layout = html.Div([
    html.H1("Gun Violence and Legislation Dashboard", style={'textAlign': 'center'}),

    dcc.Tabs(id='tabs', value='incidents', children=[
        dcc.Tab(label='Mass Shooting Incidents Map', value='incidents'),
        dcc.Tab(label='Gun Laws & Death Rates Map', value='gunlaws'),
    ]),

    html.Div(id='controls-container'),
    html.Div(id='visualization-container')
])

# === Callback for rendering controls based on selected tab ===
@app.callback(
    Output('controls-container', 'children'),
    Input('tabs', 'value')
)
def render_controls(tab):
    if tab == 'incidents':
        return html.Div([
            html.H3("Visualization Controls"),
            html.Label("Size points by:"),
            dcc.RadioItems(
                id='size-metric',
                options=[
                    {'label': 'Total Victims', 'value': 'Total Victims'},
                    {'label': 'Victims Killed', 'value': 'Victims Killed'},
                    {'label': 'Victims Injured', 'value': 'Victims Injured'},
                ],
                value='Total Victims',
                labelStyle={'display': 'block'}
            ),
            html.Label("Color points by:"),
            dcc.RadioItems(
                id='color-metric',
                options=[
                    {'label': 'Total Victims', 'value': 'Total Victims'},
                    {'label': 'Victims Killed', 'value': 'Victims Killed'},
                    {'label': 'Victims Injured', 'value': 'Victims Injured'},
                ],
                value='Victims Killed',
                labelStyle={'display': 'block'}
            ),
            html.Label("Year Range:"),
            dcc.RangeSlider(
                id='year-slider',
                min=min_year,
                max=max_year,
                value=[min_year, max_year],
                marks={i: str(i) for i in range(min_year, max_year + 1)},
                step=1
            ),
            html.Div(id='incidents-count', style={'marginTop': '20px', 'fontWeight': 'bold'}),
        ], style={'padding': '20px'})
    else:
        return html.Div([
            html.H3("Gun Laws Map Controls"),
            html.P("This map shows state-level gun law strength and gun death rates."),
            html.P("Hover over a state for details."),
        ], style={'padding': '20px'})

# === Callback for rendering the mass shooting incidents map ===
@app.callback(
    Output('visualization-container', 'children'),
    [Input('tabs', 'value'),
     Input('size-metric', 'value'),
     Input('color-metric', 'value'),
     Input('year-slider', 'value')],
    prevent_initial_call=True
)
def render_incidents_map(tab, size_metric, color_metric, year_range):
    if tab != 'incidents':
        return dash.no_update

    # Filter data by selected year range
    filtered_df = processed_shootings[processed_shootings['Year'].between(year_range[0], year_range[1])]

    # Create scatter mapbox
    fig = px.scatter_mapbox(
        filtered_df,
        lat='latitude',
        lon='longitude',
        size=size_metric,
        color=color_metric,
        hover_name='Full Location',
        hover_data=["Incident Date", "Victims Killed", "Victims Injured", "Total Victims", "State", "City Or County"],
        zoom=3,
        height=700,
        title=f"Mass Shooting Incidents Map ({filtered_df.shape[0]} incidents displayed)",
        color_continuous_scale="Reds",
        size_max=25,
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    incidents_count = f"Showing {filtered_df.shape[0]} incidents"

    return [
        dcc.Graph(figure=fig, style={'height': '80vh'}),
        html.Div(incidents_count, style={'fontWeight': 'bold', 'marginTop': '10px'})
    ]

# === Callback for rendering the gun laws choropleth map ===
@app.callback(
    Output('visualization-container', 'children', allow_duplicate=True),
    Input('tabs', 'value'),
    prevent_initial_call=True
)
def render_gunlaws_map(tab):
    if tab != 'gunlaws':
        return dash.no_update

    # Create choropleth map
    # Define reversed Reds color scale
    color_scale = px.colors.sequential.Reds[::-1]

    fig = px.choropleth(
        gun_laws_df,
        locations='State',
        locationmode="USA-states",
        color='Law Strength',
        hover_name='State',
        hover_data={'Gun Deaths': True, 'Law Strength': True},
        color_continuous_scale=color_scale,
        range_color=[0, 100],
        scope="usa",
        title="Gun Law Strength by State and Gun Death Rates",
    )

    # Layout tweaks
    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        geo=dict(bgcolor='rgba(0,0,0,0)')
    )

    fig.update_coloraxes(colorbar_title='Law Strength')

    return [dcc.Graph(figure=fig, style={'height': '80vh'})]

# === Run the app ===
if __name__ == '__main__':
    app.run(debug=True)
