import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import os

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
server = app.server

# === Load mass shooting data ===
data_path = "mass_shootings_geocoded.csv"
try:
    df = pd.read_csv(data_path)
    print(f"Loaded data with {df.shape[0]} rows and {df.shape[1]} columns")
    print("Columns in dataset:", df.columns.tolist())
except Exception as e:
    print(f"Error loading data: {e}")
    df = pd.DataFrame()

# === Clean and process the data ===
def process_data(df):
    processed_df = df.copy()

    # Clean latitude and longitude: split and convert to float
    if 'latitude' in processed_df.columns:
        processed_df[['longitude', 'latitude']] = processed_df['latitude'].str.split(',', expand=True)
        processed_df['latitude'] = pd.to_numeric(processed_df['latitude'], errors='coerce')
        processed_df['longitude'] = pd.to_numeric(processed_df['longitude'], errors='coerce')

    # Extract year from incident date
    if "Incident Date" in processed_df.columns:
        processed_df['Year'] = processed_df["Incident Date"].str.extract(r'(\d{4})')
        processed_df['Year'] = pd.to_numeric(processed_df['Year'], errors='coerce')

        # Convert to datetime for sorting
        processed_df['Date'] = pd.to_datetime(processed_df["Incident Date"], errors='coerce')

    # Calculate total victims
    if "Victims Killed" in processed_df.columns and "Victims Injured" in processed_df.columns:
        processed_df['Total Victims'] = processed_df["Victims Killed"] + processed_df["Victims Injured"]

    # Create full location string for hover info
    processed_df['Full Location'] = processed_df.apply(
        lambda row: f"{row['Address']}, {row['City Or County']}, {row['State']}, USA",
        axis=1
    )

    # Drop rows with missing coordinates
    processed_df = processed_df.dropna(subset=['latitude', 'longitude'])

    return processed_df

# Process the data
processed_df = process_data(df)

# Get min and max year for slider
if not processed_df.empty and 'Year' in processed_df.columns:
    min_year = int(processed_df['Year'].min())
    max_year = int(processed_df['Year'].max())
else:
    min_year, max_year = 2020, 2025

# === App Layout ===
app.layout = html.Div([
    html.H1("Mass Shooting Incidents Map", style={'textAlign': 'center'}),

    html.Div([
        html.Div([
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

        ], className="three columns"),

        html.Div([
            dcc.Graph(id='map-visualization', style={'height': '80vh'}),
        ], className="nine columns"),
    ], className="row"),

    html.Div([
        html.H3("Dataset Preview"),
        html.Div(
            style={'overflowX': 'auto'},
            children=[
                html.Table(
                    [html.Tr([html.Th(col) for col in df.columns])] +
                    [html.Tr([html.Td(df.iloc[i][col]) for col in df.columns])
                     for i in range(min(5, len(df)))]
                )
            ]
        )
    ], className="row"),
])

# === Callbacks ===
@app.callback(
    [Output('map-visualization', 'figure'),
     Output('incidents-count', 'children')],
    [Input('size-metric', 'value'),
     Input('color-metric', 'value'),
     Input('year-slider', 'value')]
)
def update_map(size_metric, color_metric, year_range):
    filtered_df = processed_df.copy()

    # Filter by year range
    filtered_df = filtered_df[filtered_df['Year'].between(year_range[0], year_range[1])]

    # Create the map
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
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )

    incidents_count = f"Showing {filtered_df.shape[0]} incidents"

    return fig, incidents_count

# === Run the app ===
if __name__ == '__main__':
    app.run(debug=True)
