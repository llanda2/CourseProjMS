# === Import Libraries ===
import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px

# === Initialize Dash App ===
app = dash.Dash(__name__,
                external_stylesheets=["https://cdn.jsdelivr.net/npm/bootswatch@5.3.2/dist/darkly/bootstrap.min.css"])
app.config.suppress_callback_exceptions = True
server = app.server

# === Load and Process Data ===
# === Load and clean gun laws dataset ===
gun_laws_df = pd.read_csv('./data/stateLaws.csv')
gun_laws_df.columns = gun_laws_df.columns.str.strip()  # Clean column names
gun_laws_df = gun_laws_df.rename(columns={
    'Label': 'State',
    'Strength of Gun Laws (out of 100 points)': 'Law Strength',
    'Gun Deaths per 100,000 Residents': 'Gun Deaths'
})
gun_laws_df['Law Strength'] = pd.to_numeric(gun_laws_df['Law Strength'], errors='coerce')
gun_laws_df['Gun Deaths'] = pd.to_numeric(gun_laws_df['Gun Deaths'], errors='coerce')

# === Load and clean Supreme Court cases dataset ===
sc_cases_df = pd.read_csv('./data/SCDeci.csv')
sc_cases_df.columns = sc_cases_df.columns.str.strip()
sc_cases_df = sc_cases_df.rename(columns={
    'Second Amendment Supreme Court Cases': 'Case',
    'Year of Decision': 'Year',
    'Court Justices': 'Justice',
    'Justice Decision': 'Decision Type',
    '0 - Advocacy for Gun Rights; 1 - Advocacy for Gun Control': 'Stance'
})
sc_cases_df['Year'] = pd.to_numeric(sc_cases_df['Year'], errors='coerce')
sc_cases_df['Stance'] = pd.to_numeric(sc_cases_df['Stance'], errors='coerce')

# === Load and process mass shootings data ===
shootings_df = pd.read_csv('mass_shootings_geocoded.csv')
shootings_df['latitude'] = pd.to_numeric(shootings_df['latitude'], errors='coerce')
shootings_df['longitude'] = pd.to_numeric(shootings_df['longitude'], errors='coerce')
shootings_df['Year'] = pd.to_numeric(shootings_df['Incident Date'].str.extract(r'(\d{4})')[0], errors='coerce')
shootings_df['Total Victims'] = shootings_df['Victims Killed'] + shootings_df['Victims Injured']
shootings_df['Full Location'] = shootings_df.apply(lambda row: f"{row['Address']}, {row['City Or County']}, {row['State']}, USA", axis=1)
shootings_df.dropna(subset=['latitude', 'longitude'], inplace=True)
processed_shootings = shootings_df.copy()
min_year = int(processed_shootings['Year'].min())
max_year = int(processed_shootings['Year'].max())

# === Load and clean opinion poll data ===
opinion_paths = {f"LL{i}": f"./data/LL{i}.csv" for i in range(1, 11)}

def clean_opinion_df(df):
    df = df.copy()
    df = df[~df.apply(lambda row: all(str(x).strip() in ['%', 'nan', '*'] for x in row), axis=1)]
    df.dropna(how='all', inplace=True)
    if not str(df.columns[0]).lower().startswith("date") and "X.1" in df.columns[0]:
        df.columns = df.iloc[0]
        df = df.drop(df.index[0])
    df = df[df.iloc[:, 0].astype(str).str.contains(r"\d{4}", na=False)]
    df.rename(columns={df.columns[0]: "Date"}, inplace=True)
    df_melted = df.melt(id_vars="Date", var_name="Response", value_name="Percent")
    df_melted['Percent'] = df_melted['Percent'].astype(str).str.replace('%', '', regex=False).str.replace('*', '', regex=False).str.strip()
    df_melted['Percent'] = pd.to_numeric(df_melted['Percent'], errors='coerce')
    df_melted['Date'] = pd.to_datetime(df_melted['Date'], errors='coerce')
    df_melted = df_melted.dropna(subset=['Date', 'Percent'])
    return df_melted

opinion_data = {key: clean_opinion_df(pd.read_csv(path)) for key, path in opinion_paths.items()}

# === App Layout ===
app.layout = html.Div([
    html.H1("Gun Violence and Legislation Dashboard", style={'textAlign': 'center'}),
    dcc.Tabs(id='tabs', value='incidents', children=[
        dcc.Tab(label='Mass Shooting Incidents Map', value='incidents'),
        dcc.Tab(label='Gun Laws & Death Rates Map', value='gunlaws'),
        dcc.Tab(label='Public Opinion Polls', value='opinion'),
        dcc.Tab(label='Supreme Court & 2A Cases', value='scotus')
    ]),
    html.Div(id='controls-container'),
    html.Div(id='visualization-container', children=[
        html.Div(id='incidents-graph'),
        html.Div(id='gunlaws-graph'),
        html.Div(id='opinion-graph'),
        html.Div(id='scotus-graph')
    ])
])

# === Render Controls ===
@app.callback(Output('controls-container', 'children'), Input('tabs', 'value'))
def render_controls(tab):
    if tab == 'incidents':
        return html.Div([
            html.H3("Controls for Mass Shootings"),
            dcc.RadioItems(
                id='size-metric',
                options=[{'label': label, 'value': label} for label in
                         ['Total Victims', 'Victims Killed', 'Victims Injured']],
                value='Total Victims',
                labelStyle={'display': 'block'}
            ),
            dcc.RangeSlider(
                id='year-slider',
                min=min_year,
                max=max_year,
                value=[min_year, max_year],
                marks={i: str(i) for i in range(min_year, max_year + 1)},
                step=1
            )
        ])
    elif tab == 'opinion':
        return html.Div([
            html.H3("Select a Poll Question"),
            dcc.Dropdown(
                id='opinion-selector',
                options=[{'label': k, 'value': k} for k in opinion_data.keys()],
                value='LL1'
            )
        ])
    return None

# === Mass Shootings Callback ===
@app.callback(
    Output('incidents-graph', 'children'),
    Input('tabs', 'value'),
    Input('size-metric', 'value'),
    Input('year-slider', 'value'),
    prevent_initial_call=True
)
def update_mass_shootings(tab, size_metric, year_range):
    if tab != 'incidents' or size_metric is None or year_range is None:
        return None
    filtered_df = processed_shootings[
        (processed_shootings['Year'] >= year_range[0]) &
        (processed_shootings['Year'] <= year_range[1])
    ]
    cumulative_df = pd.concat([
        filtered_df[filtered_df['Year'] <= y].assign(Cumulative_Year=y)
        for y in range(year_range[0], year_range[1] + 1)
    ])
    fig = px.scatter_mapbox(
        cumulative_df,
        lat='latitude',
        lon='longitude',
        size=size_metric,
        color_discrete_sequence=["crimson"],
        hover_name='Full Location',
        hover_data=["Incident Date", "Victims Killed", "Victims Injured", "Total Victims", "State", "City Or County"],
        animation_frame='Cumulative_Year',
        zoom=3,
        height=700,
        size_max=35
    )
    fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 40, "l": 0, "b": 0})
    return dcc.Graph(figure=fig, style={'height': '80vh'})

# === Gun Laws Callback ===
@app.callback(
    Output('gunlaws-graph', 'children'),
    Input('tabs', 'value')
)
def update_gunlaws(tab):
    if tab != 'gunlaws':
        return None
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
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    return dcc.Graph(figure=fig, style={'height': '80vh'})

# === Opinion Poll Callback ===
@app.callback(
    Output('opinion-graph', 'children'),
    Input('tabs', 'value'),
    Input('opinion-selector', 'value')
)
def update_opinion(tab, opinion_key):
    if tab != 'opinion':
        return None
    df = opinion_data.get(opinion_key)
    if df is None:
        return html.Div("No data found.")
    fig = px.line(df, x='Date', y='Percent', color='Response', title=f"Public Opinion: {opinion_key}", markers=True)
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    return dcc.Graph(figure=fig, style={'height': '80vh'})

# === SCOTUS Callback ===
@app.callback(
    Output('scotus-graph', 'children'),
    Input('tabs', 'value')
)
def update_scotus(tab):
    if tab != 'scotus':
        return None
    fig = px.histogram(
        sc_cases_df,
        x='Year',
        color='Stance',
        color_discrete_map={0: 'green', 1: 'red'},
        hover_data=['Case', 'Justice', 'Decision Type'],
        barmode='stack',
        title='Supreme Court Justices: 2nd Amendment Decisions'
    )
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0}, xaxis_title='Year', yaxis_title='Number of Opinions')
    return dcc.Graph(figure=fig, style={'height': '80vh'})

# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)
