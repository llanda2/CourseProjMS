import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import re
import numpy as np
# from dotenv import load_dotenv, find_dotenv

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
server = app.server

# Load mass shooting data
data_path = os.path.join("data", "MassShootingIncidnets.csv")
try:
    # Handle potential typo in filename (Incidnets vs Incidents)
    if not os.path.exists(data_path):
        alternative_path = os.path.join("data", "MassShootingIncidents.csv")
        if os.path.exists(alternative_path):
            data_path = alternative_path

    df = pd.read_csv(data_path)
    print(f"Loaded data with {df.shape[0]} rows and {df.shape[1]} columns")
    print("Columns in dataset:", df.columns.tolist())

except Exception as e:
    print(f"Error loading data: {e}")
    # Create an empty DataFrame with expected columns
    df = pd.DataFrame(columns=["Incident ID", "Incident Date", "State", "City Or County",
                               "Address", "Victims Killed", "Victims Injured"])


# Process the data for mapping
def process_data(df):
    processed_df = df.copy()

    # Extract year from date for filtering
    if "Incident Date" in processed_df.columns:
        processed_df['Year'] = processed_df["Incident Date"].str.extract(r'(\d{4})')

        # Try to convert to datetime for better sorting
        try:
            processed_df['Date'] = pd.to_datetime(processed_df["Incident Date"], errors='coerce')
        except:
            pass

    # Calculate total victims
    if "Victims Killed" in processed_df.columns and "Victims Injured" in processed_df.columns:
        processed_df['Total Victims'] = processed_df["Victims Killed"] + processed_df["Victims Injured"]

    # We need to geocode the addresses since we don't have latitude/longitude
    # For now, we'll use a placeholder function that returns random coordinates
    # In a real application, you would use a geocoding service like Google Maps API, Nominatim, etc.

    # Create full location string for potential geocoding
    processed_df['Full Location'] = processed_df.apply(
        lambda row: f"{row['Address']}, {row['City Or County']}, {row['State']}, USA"
        if all(col in row for col in ['Address', 'City Or County', 'State']) else None,
        axis=1
    )

    # Placeholder geocoding function (replace with actual geocoding in production)
    def mock_geocode(locations):
        # This is just for demonstration purposes
        # USA rough bounding box
        lats = np.random.uniform(25, 49, size=len(locations))
        lons = np.random.uniform(-125, -65, size=len(locations))

        # Try to make the coordinates somewhat match real locations
        for i, loc in enumerate(locations):
            # Extract state
            if isinstance(loc, str) and "Texas" in loc:
                lats[i] = np.random.uniform(26, 36)
                lons[i] = np.random.uniform(-106, -93)
            elif isinstance(loc, str) and "California" in loc:
                lats[i] = np.random.uniform(32, 42)
                lons[i] = np.random.uniform(-124, -114)
            elif isinstance(loc, str) and "New York" in loc:
                lats[i] = np.random.uniform(40, 45)
                lons[i] = np.random.uniform(-80, -73)
            # Add more states as needed

        return lats, lons

    # Get coordinates
    processed_df['latitude'], processed_df['longitude'] = mock_geocode(processed_df['Full Location'])

    return processed_df


# Process the data
processed_df = process_data(df)

# Get the min and max years for the slider
if 'Year' in processed_df.columns:
    min_year = int(processed_df['Year'].astype(float).min()) if not processed_df['Year'].isna().all() else 2020
    max_year = int(processed_df['Year'].astype(float).max()) if not processed_df['Year'].isna().all() else 2025
else:
    min_year = 2020
    max_year = 2025

# App layout
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
        html.P(
            "Note: This map uses simulated coordinates for demonstration. In a production environment, you would use a geocoding service to get accurate coordinates."),
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

    html.Div([
        html.H3("Implementation Notes"),
        html.P([
            "This dashboard uses simulated geographic coordinates since the original data does not contain latitude/longitude information. ",
            "For a production version, you would need to implement real geocoding using a service like Google Maps API, Nominatim (OpenStreetMap), or similar."
        ]),
        html.P([
            "Steps to implement real geocoding:",
            html.Br(),
            "1. Use the 'Full Location' column that combines address, city, and state",
            html.Br(),
            "2. Send each location to a geocoding service",
            html.Br(),
            "3. Store the results in a cache to avoid repeated API calls",
            html.Br(),
            "4. Add error handling for locations that can't be geocoded"
        ]),
    ], className="row"),
])


# Callback to update map
@app.callback(
    [Output('map-visualization', 'figure'),
     Output('incidents-count', 'children')],
    [Input('size-metric', 'value'),
     Input('color-metric', 'value'),
     Input('year-slider', 'value')]
)
def update_map(size_metric, color_metric, year_range):
    # Create a copy of the dataframe to work with
    filtered_df = processed_df.copy()

    # Apply year filter if available
    if 'Year' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Year'].astype(float).between(year_range[0], year_range[1])]

    # Create the map
    fig = px.scatter_mapbox(
        filtered_df,
        lat='latitude',
        lon='longitude',
        size=size_metric if size_metric in filtered_df.columns else None,
        color=color_metric if color_metric in filtered_df.columns else None,
        hover_name='Full Location',
        hover_data=["Incident Date", "Victims Killed", "Victims Injured", "Total Victims", "State", "City Or County"],
        zoom=3,
        height=700,
        title=f"Mass Shooting Incidents Map ({filtered_df.shape[0]} incidents displayed)",
        color_continuous_scale="Reds",
        size_max=25,
    )

    # Update map style
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

    # Update incidents count
    incidents_count = f"Showing {filtered_df.shape[0]} incidents"

    return fig, incidents_count


# Run the app
if __name__ == '__main__':
    app.run(debug=True)