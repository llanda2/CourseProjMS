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
            hover_data=["Incident Date", "Victims Killed", "Victims Injured", "Total Victims", "State",
                        "City Or County"],
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

    # === Supreme Court Timeline ===
    @app.callback(Output('scotus-graph', 'children'), Input('tabs', 'value'))
    def render_scotus_timeline(tab):
        if tab != 'scotus':
            return None

        df = DATA['sc_cases_df'].copy()

        # Get unique cases and their years
        unique_cases = df[['Case', 'Year', 'Stance']].drop_duplicates()

        # Create figure using go.Figure for more control
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(specs=[[{"secondary_y": False}]])

        # Create color mapping for cases based on stance
        colors = {0: '#1E88E5', 1: '#D81B60'}  # Blue for gun rights (0), Red for gun control (1)

        # Add a case marker for each unique case
        for i, case in unique_cases.iterrows():
            case_name = case['Case']
            case_year = case['Year']
            case_details = df[(df['Case'] == case_name) & (df['Year'] == case_year)]

            # Get majority and dissent
            majority = \
            case_details[case_details['Decision Type'].str.contains("Majority|Per Curiam", case=False, na=False)][
                'Justice'].tolist()
            dissent = case_details[case_details['Decision Type'].str.contains("Dissent", case=False, na=False)][
                'Justice'].tolist()

            # Get stance
            stance_value = case['Stance']
            stance_text = "Gun Rights Advocacy" if stance_value == 0 else "Gun Control Advocacy"

            # Create hover text
            hover_text = f"<b>{case_name}</b> ({case_year})<br>"
            hover_text += f"Stance: {stance_text}<br>"
            hover_text += f"Majority: {', '.join(majority)}<br>"
            hover_text += f"Dissent: {', '.join(dissent)}"

            # Add marker for the case
            fig.add_trace(
                go.Scatter(
                    x=[case_year],
                    y=[case_name],
                    mode='markers',
                    marker=dict(
                        symbol='square',
                        size=18,
                        color=colors[stance_value],
                        line=dict(width=2, color='DarkSlateGrey')
                    ),
                    name=case_name,
                    text=hover_text,
                    hoverinfo='text',
                    customdata=[[case_name, case_year]],
                    showlegend=False
                )
            )

        # Add case names and horizontal lines
        y_values = unique_cases['Case'].unique()
        min_year = int(unique_cases['Year'].min())
        max_year = int(unique_cases['Year'].max())

        # Add horizontal lines connecting cases
        for i, case in enumerate(y_values):
            fig.add_shape(
                type="line",
                x0=min_year - 0.5,
                x1=max_year + 0.5,
                y0=case,
                y1=case,
                line=dict(color="LightGrey", width=1, dash="dot"),
                layer="below"
            )

        # Update layout
        fig.update_layout(
            title='Supreme Court Second Amendment Cases Timeline',
            xaxis=dict(
                title='Year',
                tickmode='linear',
                dtick=1,
                gridcolor='LightGrey',
                range=[min_year - 0.5, max_year + 0.5]
            ),
            yaxis=dict(
                title=None,
                autorange="reversed"  # Most recent cases at the top
            ),
            margin={"r": 10, "t": 40, "l": 10, "b": 10},
            height=600,
            hovermode='closest',
            plot_bgcolor='white',
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            )
        )

        # Add legend for case stances
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode='markers',
                marker=dict(size=10, color=colors[0]),
                name='Gun Rights Decision'
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode='markers',
                marker=dict(size=10, color=colors[1]),
                name='Gun Control Decision'
            )
        )

        # Add vertical line for current year
        fig.add_shape(
            type="line",
            x0=2025, x1=2025,
            y0=0, y1=1,
            yref="paper",
            line=dict(color="red", width=2, dash="dash"),
        )
        fig.add_annotation(
            x=2025, y=1.02,
            yref="paper",
            text="Present Day",
            showarrow=False,
            font=dict(color="red")
        )

        # Add click event support for detailed view
        return dcc.Graph(
            id='scotus-timeline',
            figure=fig,
            style={'height': '70vh'},
            config={'displayModeBar': True}
        )

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

        if tab == 'scotus' and trigger == 'scotus-timeline' and clickData:
            # Extract case info from customdata
            clicked_case = clickData['points'][0]['customdata'][0]
            clicked_year = int(clickData['points'][0]['customdata'][1])

            # Get the dataframe and print information for debugging
            df = DATA['sc_cases_df']
            print(f"Looking for case: {clicked_case}, year: {clicked_year}")
            print(f"Available columns: {df.columns.tolist()}")

            # Make case name matching more robust by checking exact match
            case_df = df[(df['Year'] == clicked_year) & (df['Case'] == clicked_case)]

            if case_df.empty:
                print(f"Case not found. Available cases: {df['Case'].unique()}")
                return html.Div(f"Case details not found for {clicked_case} ({clicked_year}).")

            # Get unique case information
            # Try different column names for the description
            description = None
            description_columns = ['Brief Synopsis of Case', 'Quick Summary', 'Synopsis', 'Description']

            for col in description_columns:
                if col in case_df.columns and not pd.isna(case_df[col].iloc[0]) and case_df[col].iloc[0] != "":
                    description = case_df[col].iloc[0]
                    break

            if description is None:
                description = "No description available."

            # Determine stance
            stance_value = case_df['Stance'].iloc[0] if 'Stance' in case_df.columns else None
            if stance_value is not None:
                stance = "Gun Rights Advocacy" if stance_value == 0 else "Gun Control Advocacy"
            else:
                stance = "Stance information not available"

            # Get justices by opinion type
            # Use a more robust method to identify decision types
            def get_justices_by_decision(df, decision_type_pattern):
                if 'Decision Type' in df.columns and 'Justice' in df.columns:
                    filtered = df[df['Decision Type'].str.contains(decision_type_pattern, case=False, na=False)]
                    return filtered['Justice'].tolist() if not filtered.empty else []
                return []

            majority = get_justices_by_decision(case_df, "Majority|Per Curiam")
            concur = get_justices_by_decision(case_df, "Concur")
            dissent = get_justices_by_decision(case_df, "Dissent")

            # Create a detailed card with case information
            return dbc.Card([
                dbc.CardHeader(html.H4(clicked_case, className="card-title")),
                dbc.CardBody([
                    html.H5(f"Year: {clicked_year}", className="card-subtitle mb-2 text-muted"),
                    html.P(f"Description: {description}", className="card-text"),
                    html.P(f"Stance: {stance}", className="card-text",
                           style={'color': 'blue' if stance == 'Gun Rights Advocacy' else 'red',
                                  'fontWeight': 'bold'}),
                    html.Hr(),
                    html.H5("Opinion Breakdown:"),
                    html.P(f"Majority Opinion: {', '.join(majority)}",
                           style={'color': 'green'}) if majority else html.P("Majority Opinion information unavailable",
                                                                             style={'fontStyle': 'italic'}),
                    html.P(f"Concurring Opinion: {', '.join(concur)}", style={'color': 'blue'}) if concur else None,
                    html.P(f"Dissenting Opinion: {', '.join(dissent)}", style={'color': 'red'}) if dissent else html.P(
                        "No dissenting opinions", style={'fontStyle': 'italic'})
                ])
            ], style={"marginTop": "2rem", "boxShadow": "0 0 10px rgba(0,0,0,0.2)"})

        # Default controls for the scotus tab
        if tab == 'scotus':
            return html.Div([
                html.H3("Supreme Court Second Amendment Cases"),
                html.P("Click on a case in the timeline to view detailed information."),
                html.Hr(),
                html.P("This timeline shows major Supreme Court cases related to the Second Amendment and gun rights. "
                       "Each marker represents a case, with color indicating whether the decision favored gun rights or gun control."),
            ])

        # Controls for other tabs
        elif tab == 'incidents':
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
                    options=[{'label': k, 'value': k} for k in DATA['opinion_data'].keys()],
                    value='LL1'
                )
            ])

        return None