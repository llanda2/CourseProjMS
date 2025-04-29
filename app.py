# === Import Libraries ===
import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px

# === Initialize Dash App ===
app = dash.Dash(__name__,
                external_stylesheets=["https://cdn.jsdelivr.net/npm/bootswatch@5.3.2/dist/darkly/bootstrap.min.css"])
app.config.suppress_callback_exceptions = True
server = app.server

# === Load and Process Data ===

# Mass shootings data
shootings_df = pd.read_csv('mass_shootings_geocoded.csv')


def process_shootings(df):
    """Cleans and processes mass shooting dataset."""
    df = df.copy()
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df['Year'] = pd.to_numeric(df["Incident Date"].str.extract(r'(\d{4})')[0], errors='coerce')
    df['Total Victims'] = df["Victims Killed"] + df["Victims Injured"]
    df['Full Location'] = df.apply(lambda row: f"{row['Address']}, {row['City Or County']}, {row['State']}, USA",
                                   axis=1)
    df = df.dropna(subset=['latitude', 'longitude'])
    df['Cumulative Year'] = df['Year']
    return df


processed_shootings = process_shootings(shootings_df)
min_year = int(processed_shootings['Year'].min())
max_year = int(processed_shootings['Year'].max())

# Gun laws data
gun_laws_df = pd.read_csv('data/stateLaws.csv')
gun_laws_df.rename(columns={
    'Label': 'State',
    'Strength of Gun Laws (out of 100 points)': 'Law Strength',
    'Gun Deaths per 100,000 Residents': 'Gun Deaths'
}, inplace=True)

# Public opinion data
opinion_paths = {f"LL{i}": f"./data/LL{i}.csv" for i in range(1, 11)}
opinion_data = {key: pd.read_csv(path) for key, path in opinion_paths.items()}

# === App Layout ===
app.layout = html.Div([
    html.H1("Gun Violence and Legislation Dashboard", style={'textAlign': 'center'}),

    dcc.Tabs(id='tabs', value='incidents', children=[
        dcc.Tab(label='Mass Shooting Incidents Map', value='incidents'),
        dcc.Tab(label='Gun Laws & Death Rates Map', value='gunlaws'),
        dcc.Tab(label='Public Opinion Polls', value='opinion')
    ]),

    html.Div(id='controls-container'),
    html.Div(id='visualization-container')
])


# === Callback: Render Controls by Tab ===
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
                options=[{'label': label, 'value': label} for label in
                         ['Total Victims', 'Victims Killed', 'Victims Injured']],
                value='Total Victims',
                labelStyle={'display': 'block'}
            ),
            html.Label("Color points by:"),
            dcc.RadioItems(
                id='color-metric',
                options=[{'label': label, 'value': label} for label in
                         ['Total Victims', 'Victims Killed', 'Victims Injured']],
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
            html.Div(id='incidents-count', style={'marginTop': '20px', 'fontWeight': 'bold'})
        ], style={'padding': '20px'})

    elif tab == 'gunlaws':
        return html.Div([
            html.H3("Gun Laws Map Controls"),
            html.P("This map shows state-level gun law strength and gun death rates."),
            html.P("Hover over a state for details.")
        ], style={'padding': '20px'})

    elif tab == 'opinion':
        return html.Div([
            html.H3("Select a Poll Question"),
            dcc.Dropdown(  # ✅ Only ONE Dropdown
                id='opinion-selector',
                options=[
                    {'label': 'Firearm Law Strictness (1990s–2000s Data)', 'value': 'LL1'},
                    {'label': 'Gun Ownership (1959–1990s Data, Yes Only)', 'value': 'LL2'},
                    {'label': 'Firearm Law Strictness (Recent Data 2022–2024)', 'value': 'LL3'},
                    {'label': 'Gun Ownership (Recent Data 2021–2024)', 'value': 'LL4'},
                    {'label': 'Satisfaction with U.S. Gun Policies (2022–2025)', 'value': 'LL5'},
                    {'label': 'Desired Changes to Gun Laws Among Dissatisfied Respondents', 'value': 'LL6'},
                    {'label': 'Gun Ownership Breakdown: Personal vs Household (2021–2024)', 'value': 'LL7'},
                    {'label': 'Support for Handgun Ban (2021–2024)', 'value': 'LL8'},
                    {'label': 'Support for Assault Rifle Ban (2019–2024)', 'value': 'LL9'},
                    {'label': 'Importance of Gun Control in Voting Decisions (2015–2024)', 'value': 'LL10'},
                    {'label': 'Reasons for Gun Ownership (Hunting and Others)', 'value': 'LL11'},
                ],
                value='LL1',  # Default selected value
                clearable=False,
                style={"color": "black"}
            )
        ], style={'padding': '20px'})


# === Callback: Render Visualizations ===

# Mass Shooting Incidents Map
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

    filtered_df = processed_shootings[
        (processed_shootings['Year'] >= year_range[0]) &
        (processed_shootings['Year'] <= year_range[1])
        ]

    expanded_rows = []
    for year in range(year_range[0], year_range[1] + 1):
        year_data = filtered_df[filtered_df['Year'] <= year].copy()
        year_data['Cumulative Year'] = year
        expanded_rows.append(year_data)

    cumulative_df = pd.concat(expanded_rows, ignore_index=True)

    fig = px.scatter_mapbox(
        cumulative_df,
        lat='latitude',
        lon='longitude',
        size=size_metric,
        color_discrete_sequence=["crimson"],
        hover_name='Full Location',
        hover_data=["Incident Date", "Victims Killed", "Victims Injured", "Total Victims", "State", "City Or County"],
        animation_frame='Cumulative Year',
        zoom=3,
        height=700,
        size_max=35
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )

    incidents_count = f"Showing {filtered_df.shape[0]} incidents"
    return [
        dcc.Graph(figure=fig, style={'height': '80vh'}),
        html.Div(incidents_count, style={'fontWeight': 'bold', 'marginTop': '10px'})
    ]


# Gun Laws Choropleth Map
@app.callback(
    Output('visualization-container', 'children', allow_duplicate=True),
    Input('tabs', 'value'),
    prevent_initial_call=True
)
def render_gunlaws_map(tab):
    if tab != 'gunlaws':
        return dash.no_update

    fig = px.choropleth(
        gun_laws_df,
        locations='State',
        locationmode="USA-states",
        color='Law Strength',
        hover_name='State',
        hover_data={'Gun Deaths': True, 'Law Strength': True},
        color_continuous_scale=px.colors.sequential.Reds[::-1],
        range_color=[0, 100],
        scope="usa",
        title="Gun Law Strength by State and Gun Death Rates"
    )
    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        geo=dict(bgcolor='rgba(0,0,0,0)')
    )
    fig.update_coloraxes(colorbar_title='Law Strength')

    return [dcc.Graph(figure=fig, style={'height': '80vh'})]


# Public Opinion Polls
@app.callback(
    Output('visualization-container', 'children', allow_duplicate=True),
    [Input('tabs', 'value'),
     Input('opinion-selector', 'value')],
    prevent_initial_call=True
)
def render_opinion_tab(tab, opinion_key):
    if tab != 'opinion' or opinion_key is None:
        return dash.no_update

    df = opinion_data[opinion_key].copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0])
    df.rename(columns={df.columns[0]: "Date"}, inplace=True)

    df_melted = df.melt(id_vars="Date", var_name="Response", value_name="Percent")
    df_melted['Percent'] = pd.to_numeric(df_melted['Percent'], errors='coerce')

    fig = px.line(
        df_melted, x='Date', y='Percent', color='Response',
        title=f"Public Opinion: {opinion_key}", markers=True
    )
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})

    return dcc.Graph(figure=fig, style={'height': '80vh'})


# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)
