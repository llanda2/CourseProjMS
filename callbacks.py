# === callbacks.py ===
from dash import dcc, html, Input, Output, State, callback_context
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

def register_callbacks(app, DATA):
    shootings_df = DATA['shootings_df']
    min_year = int(shootings_df['Year'].min())
    max_year = int(shootings_df['Year'].max())

    # === Mass Shooting Map ===
    @app.callback(
        Output('incidents-graph', 'children'),
        Input('tabs', 'value'),
        Input('size-metric', 'value'),
        Input('year-slider', 'value')
    )
    def update_mass_shootings(tab, size_metric, year_range):
        if tab != 'incidents' or size_metric is None or year_range is None:
            return None
        filtered_df = shootings_df[(shootings_df['Year'] >= year_range[0]) & (shootings_df['Year'] <= year_range[1])]
        cumulative_df = pd.concat([
            filtered_df[filtered_df['Year'] <= y].assign(Cumulative_Year=y)
            for y in range(year_range[0], year_range[1] + 1)
        ])
        fig = px.scatter_mapbox(
            cumulative_df,
            lat='latitude', lon='longitude',
            size=size_metric,
            color_discrete_sequence=["crimson"],
            hover_name='Full Location',
            hover_data=["Incident Date", "Victims Killed", "Victims Injured", "Total Victims", "State", "City Or County"],
            animation_frame='Cumulative_Year',
            zoom=3, height=700, size_max=35
        )
        fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 40, "l": 0, "b": 0})
        return dcc.Graph(figure=fig, style={'height': '80vh'})

    # === Gun Laws Map ===
    @app.callback(
        Output('gunlaws-graph', 'children'),
        Input('tabs', 'value')
    )
    def update_gunlaws(tab):
        if tab != 'gunlaws':
            return None
        df = DATA['gun_laws_df']
        fig = px.choropleth(
            df,
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

    # === Opinion Polls Line Chart ===
    @app.callback(
        Output('opinion-graph', 'children'),
        Input('tabs', 'value'),
        Input('opinion-selector', 'value')
    )
    def update_opinion(tab, opinion_key):
        if tab != 'opinion':
            return None
        df = DATA['opinion_data'].get(opinion_key)
        if df is None:
            return html.Div("No data found.")
        fig = px.line(df, x='Date', y='Percent', color='Response', title=f"Public Opinion: {opinion_key}", markers=True)
        fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
        return dcc.Graph(figure=fig, style={'height': '80vh'})

    @app.callback(Output('scotus-graph', 'children'), Input('tabs', 'value'))
    def render_scotus_tab(tab):
        if tab != 'scotus':
            return None

        df = DATA['sc_cases_df'].copy()

        # Create one row per case-justice combo (already flattened)
        df['hover_label'] = df['Case'] + " (" + df['Year'].astype(str) + ") - " + df['Justice'] + " [" + df[
            'Decision Type'] + "]"

        fig = px.scatter(
            df,
            x='Year',
            y='Justice',  # ✅ Now we can render something on the y-axis
            color='Stance',
            hover_name='hover_label',
            custom_data=['Case', 'Year'],
            color_discrete_map={0: 'green', 1: 'red'},
            title='Supreme Court Justices: 2A Case Participation'
        )

        fig.update_traces(marker=dict(size=10))
        fig.update_layout(
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            height=500,
            yaxis_title=None,
            xaxis_title='Year',
            showlegend=False
        )

        return dcc.Graph(id='scotus-timeline', figure=fig, style={'height': '60vh'})

    # === Combined Controls & SCOTUS Detail View ===
    @app.callback(
        Output('controls-container', 'children'),
        Input('tabs', 'value'),
        Input('scotus-timeline', 'clickData'),
        prevent_initial_call=False
    )
    def update_controls(tab, clickData):
        ctx = callback_context
        trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        if trigger == 'scotus-timeline' and clickData:
            clicked_year = clickData['points'][0]['customdata'][1]
            clicked_case = clickData['points'][0]['customdata'][0]

            df = DATA['sc_cases_df']
            case_df = df[(df['Year'] == clicked_year) & (df['Case'] == clicked_case)]

            if case_df.empty:
                return html.Div("Case not found.")

            short_description = case_df['Brief Synopsis of Case'].iloc[0]
            stance = "Gun Rights Advocacy" if case_df['Stance'].iloc[0] == 0 else "Gun Control Advocacy"
            majority = case_df[case_df['Decision Type'].str.contains("Majority|Per Curiam", case=False, na=False)]['Justice'].tolist()
            dissent = case_df[case_df['Decision Type'].str.contains("Dissent", case=False, na=False)]['Justice'].tolist()

            return dbc.Card([
                dbc.CardBody([
                    html.H4(clicked_case, className="card-title"),
                    html.P(f"Year: {clicked_year}"),
                    html.P(f"Short description: {short_description}"),
                    html.P(f"Stance: {stance}"),
                    html.P(f"Majority Justices: {', '.join(majority)}", style={'color': 'green'}),
                    html.P(f"Dissenting Justices: {', '.join(dissent)}", style={'color': 'red'}),
                ])
            ], style={"marginTop": "2rem", "boxShadow": "0 0 10px rgba(0,0,0,0.2)"})

        if tab == 'incidents':
            return html.Div([
                html.H3("Controls for Mass Shootings"),
                dcc.RadioItems(
                    id='size-metric',
                    options=[{'label': label, 'value': label} for label in ['Total Victims', 'Victims Killed', 'Victims Injured']],
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
                    options=[{'label': k, 'value': k} for k in DATA['opinion_data'].keys()],
                    value='LL1'
                )
            ])
        elif tab == 'scotus':
            return html.H3("Supreme Court Second Amendment Cases")

        return None
