import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import os


def create_dashboard(inventory_json_path, summary_csv_path, country_mapping_file=None, country_summary_path=None):
    """
    Create a Dash application to visualize the crop inventory.
    """
    # Check if files exist
    for path in [inventory_json_path, summary_csv_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
    
    print(f"Loading data from {inventory_json_path} and {summary_csv_path}")
    
    # Load the data
    try:
        with open(inventory_json_path, 'r') as f:
            inventory = json.load(f)
        
        summary_df = pd.read_csv(summary_csv_path)
        
        # Load country summary if available
        country_df = None
        if country_summary_path and os.path.exists(country_summary_path):
            country_df = pd.read_csv(country_summary_path)
        
    except Exception as e:
        raise Exception(f"Error loading data: {e}")
        
    # Import country mapping
    try:
        from inventory_utils import load_country_mapping
        country_mapping = load_country_mapping(country_mapping_file)
    except ImportError:
        # Simple fallback
        country_mapping = {code: f"Country {code}" for code in summary_df['country_code'].unique()}
    
    # Check if country mapping is available
    country_names = pd.read_csv('/Users/michaelfoley/Library/CloudStorage/GoogleDrive-mfoley@g.harvard.edu/My Drive/Subnational_Yield_Database/helper_files/country_codes_with_iso3.csv')
    
    # Add country names to summary dataframe
    summary_df['country_name'] = summary_df['country_code'].map(
        lambda x: country_mapping.get(x, f"Country {x}")
    )
    
    # Match summary_df country codes to ISO2_Code in country_df and extract Country_Name
    summary_df = summary_df.merge(country_names[['ISO2_Code', 'ISO3_Code', 'Country_Name']], left_on='country_code', right_on='ISO2_Code', how='left')
    summary_df['country_name'] = summary_df['Country_Name']
    summary_df['map_code'] = summary_df['ISO3_Code']
    print(summary_df['map_code'].unique())
    #summary_df.drop(columns=['ISO2_Code', 'ISO3_Code', 'Country_Name'], inplace=True)
    
    # Fix any potential NaN issues in the DataFrame
    for col in ['year_min', 'year_max']:
        if col in summary_df.columns:
            # Convert non-numeric values to NaN, then fill with sensible defaults
            summary_df[col] = pd.to_numeric(summary_df[col], errors='coerce')
    
    # Expand the years column into a list of years
    if 'years' in summary_df.columns and isinstance(summary_df['years'].iloc[0], str):
        summary_df['years'] = summary_df['years'].apply(
            lambda x: [int(y) for y in x.strip('[]').split(',') if y.strip()]
        )
    
    # Default values for year slider
    min_year = summary_df['year_min'].min() if not pd.isna(summary_df['year_min'].min()) else 1900
    max_year = summary_df['year_max'].max() if not pd.isna(summary_df['year_max'].max()) else 2023
    
    # Display clear warnings for any data issues
    print(f"Data summary: {len(summary_df)} records, {summary_df['country_code'].nunique()} countries, {summary_df['crop'].nunique()} crops")
    print(f"Year range: {min_year} to {max_year}")
    
    # Initialize Dash app
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = "Crop Data Inventory Dashboard"
    
    # Define the layout
    app.layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("Crop Data Inventory Dashboard", className="text-center my-4"),
                html.P("Explore crop data availability across countries, years, and metrics.", className="lead text-center")
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Data Overview"),
                    dbc.CardBody([
                        html.Div([
                            html.H4(f"Countries: {summary_df['country_code'].nunique()}", className="d-inline-block me-4"),
                            html.H4(f"Crops: {summary_df['crop'].nunique()}", className="d-inline-block me-4"),
                            html.H4(f"Year Range: {int(min_year)}-{int(max_year)}", className="d-inline-block")
                        ], className="mb-3"),
                        
                        html.Div([
                            html.Div([
                                html.B("Area Planted: "),
                                f"{summary_df['has_area_planted'].mean() * 100:.1f}% of records"
                            ], className="mb-2"),
                            html.Div([
                                html.B("Area Harvested: "),
                                f"{summary_df['has_area_harvested'].mean() * 100:.1f}% of records"
                            ], className="mb-2"),
                            html.Div([
                                html.B("Quantity Produced: "),
                                f"{summary_df['has_quantity'].mean() * 100:.1f}% of records"
                            ], className="mb-2"),
                            html.Div([
                                html.B("Production: "),
                                f"{summary_df['has_production'].mean() * 100:.1f}% of records"
                            ], className="mb-2"),
                        ], className="mb-3"),
                    ])
                ], className="mb-4")
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Filters"),
                    dbc.CardBody([
                        html.Label("Select Countries:"),
                        dcc.Dropdown(
                            id="country-dropdown",
                            options=[
                                {
                                    "label": name, 
                                    "value": code
                                }
                                for code, name in sorted(
                                    zip(summary_df['country_code'].unique(), summary_df['country_name'].unique()), 
                                    key=lambda x: x[1]  # Sort by country name
                                )
                            ],
                            multi=True,
                            placeholder="Select countries...",
                            className="mb-3"
                        ),
                        
                        html.Label("Select Crops:"),
                        dcc.Dropdown(
                            id="crop-dropdown",
                            options=[
                                {"label": crop, "value": crop}
                                for crop in sorted(summary_df['crop'].unique())
                            ],
                            multi=True,
                            placeholder="Select crops...",
                            className="mb-3"
                        ),
                        
                        html.Label("Year Range:"),
                        dcc.RangeSlider(
                            id="year-slider",
                            min=int(min_year),
                            max=int(max_year),
                            step=1,
                            marks={i: str(i) for i in range(
                                int(min_year),
                                int(max_year) + 1,
                                max(1, int((max_year - min_year) / 10))
                            )},
                            value=[int(min_year), int(max_year)],
                            className="mb-3"
                        ),
                        
                        html.Label("Required Indicators:"),
                        dbc.Checklist(
                            options=[
                                {"label": "Area Planted", "value": "area_planted"},
                                {"label": "Area Harvested", "value": "area_harvested"},
                                {"label": "Quantity Produced", "value": "quantity"},
                                {"label": "Production", "value": "production"}
                            ],
                            value=[],
                            id="metrics-checklist",
                            inline=True,
                            className="mb-3"
                        ),
                        
                        dbc.Button("Reset Filters", id="reset-button", color="secondary", className="mt-2")
                    ])
                ], className="mb-4")
            ], md=4),
            
            dbc.Col([
                dbc.Tabs([
                    dbc.Tab([
                        dcc.Graph(id="map-graph", style={"height": "70vh"})
                    ], label="Geographic View"),
                    
                    dbc.Tab([
                        dcc.Graph(id="heatmap-graph", style={"height": "70vh"})
                    ], label="Data Coverage Heatmap"),
                    
                    dbc.Tab([
                        dcc.Graph(id="indicator-graph", style={"height": "70vh"})
                    ], label="Indicator Availability")
                ])
            ], md=8)
        ]),
        
        dbc.Row([
            dbc.Col([
                html.H3("Inventory Details", className="mt-4"),
                dbc.Card([
                    dbc.CardBody([
                        html.Div(id="summary-stats"),
                        html.Hr(),
                        html.Div(id="data-table")
                    ])
                ])
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                html.Footer([
                    html.P("Crop Data Inventory Tool - Created using Python, Dash, and Plotly", className="text-center mt-4")
                ])
            ])
        ])
    ], fluid=True)
    
    # Define callbacks
    @app.callback(
        [
            Output("map-graph", "figure"),
            Output("heatmap-graph", "figure"),
            Output("indicator-graph", "figure"),
            Output("summary-stats", "children"),
            Output("data-table", "children")
        ],
        [
            Input("country-dropdown", "value"),
            Input("crop-dropdown", "value"),
            Input("year-slider", "value"),
            Input("metrics-checklist", "value")
        ]
    )
    def update_graphs(selected_countries, selected_crops, year_range, required_metrics):
        # Filter the dataframe based on selections
        filtered_df = summary_df.copy()
        
        if selected_countries:
            filtered_df = filtered_df[filtered_df['country_code'].isin(selected_countries)]
        
        if selected_crops:
            filtered_df = filtered_df[filtered_df['crop'].isin(selected_crops)]
        
        # Filter by years if we have valid year data
        if year_range and not (pd.isna(filtered_df['year_min']).all() or pd.isna(filtered_df['year_max']).all()):
            filtered_df = filtered_df[
                (filtered_df['year_min'] >= year_range[0]) & 
                (filtered_df['year_max'] <= year_range[1])
            ]
        
        # Filter by required metrics
        if required_metrics:
            for metric, column in zip(
                ['area_planted', 'area_harvested', 'quantity', 'production'],
                ['has_area_planted', 'has_area_harvested', 'has_quantity', 'has_production']
            ):
                if metric in required_metrics:
                    filtered_df = filtered_df[filtered_df[column] == True]
        
        # Create map figure - Using ISO3 codes for better map visualization
        if not filtered_df.empty:
            # Group data by country
            map_data = filtered_df.groupby(['map_code', 'country_name']).agg({
                'crop': 'nunique',
                }).reset_index()

            # Create choropleth map
            map_fig = px.choropleth(
                map_data,
                locations='map_code',
                color='crop',
                hover_name='country_name',
                locationmode='ISO-3',  # Explicitly use ISO-3 codes for mapping
                color_continuous_scale=px.colors.sequential.Viridis,
                labels={'crop': 'Number of Crops'},
                title="Crop Data Coverage by Country"
            )
            
            # Improve map layout
            map_fig.update_layout(
                geo=dict(
                    showframe=False,
                    showcoastlines=True,
                    projection_type='equirectangular'
                ),
                margin={"r":0,"t":40,"l":0,"b":0}
            )
        else:
            map_fig = go.Figure()
            map_fig.update_layout(
                title="No data available for the selected filters"
            )
        
        # Create heatmap figure
        if not filtered_df.empty:
            # Different heatmap types based on selection
            if selected_crops and len(selected_crops) == 1 and len(filtered_df['country_code'].unique()) > 1:
                # Case 1: One crop, multiple countries - Show Countries x Years
                heatmap_title = f"Data Availability: {selected_crops[0]} by Country and Year"
                
                # Create a matrix of countries x years
                all_years = set()
                for years_list in filtered_df['years']:
                    all_years.update(years_list)
                all_years = sorted(list(all_years))
                
                # Create a new dataframe for the heatmap
                country_year_data = []
                
                for _, row in filtered_df.iterrows():
                    country = row['country_name']
                    for year in row['years']:
                        country_year_data.append({
                            'Country': country,
                            'Year': year,
                            'Has Data': 1  # Binary presence indicator
                        })
                
                if country_year_data:
                    country_year_df = pd.DataFrame(country_year_data)
                    
                    # Pivot to create the heatmap matrix
                    heatmap_df = country_year_df.pivot_table(
                        index='Country',
                        columns='Year',
                        values='Has Data',
                        aggfunc='sum',
                        fill_value=0
                    )
                    
                    # Binary heatmap (has data or not)
                    heatmap_df = (heatmap_df > 0).astype(int)
                    
                    # Create the heatmap
                    heatmap_fig = px.imshow(
                        heatmap_df,
                        color_continuous_scale=[[0, 'white'], [1, 'green']],
                        labels=dict(x="Year", y="Country", color="Has Data"),
                        title=heatmap_title
                    )
                    
                    # Improve layout
                    heatmap_fig.update_layout(
                        xaxis=dict(tickmode='array', tickvals=list(heatmap_df.columns)),
                        coloraxis_showscale=False
                    )
                else:
                    heatmap_fig = go.Figure()
                    heatmap_fig.update_layout(title="Insufficient data for heatmap")
                
            elif selected_countries and len(selected_countries) == 1 and len(filtered_df['crop'].unique()) > 1:
                # Case 2: One country, multiple crops - Show Crops x Years
                country_name = filtered_df['country_name'].iloc[0]
                heatmap_title = f"Data Availability: {country_name} by Crop and Year"
                
                # Create a matrix of crops x years
                all_years = set()
                for years_list in filtered_df['years']:
                    all_years.update(years_list)
                all_years = sorted(list(all_years))
                
                # Create a new dataframe for the heatmap
                crop_year_data = []
                
                for _, row in filtered_df.iterrows():
                    crop = row['crop']
                    for year in row['years']:
                        crop_year_data.append({
                            'Crop': crop,
                            'Year': year,
                            'Has Data': 1  # Binary presence indicator
                        })
                
                if crop_year_data:
                    crop_year_df = pd.DataFrame(crop_year_data)
                    
                    # Pivot to create the heatmap matrix
                    heatmap_df = crop_year_df.pivot_table(
                        index='Crop',
                        columns='Year',
                        values='Has Data',
                        aggfunc='sum',
                        fill_value=0
                    )
                    
                    # Binary heatmap (has data or not)
                    heatmap_df = (heatmap_df > 0).astype(int)
                    
                    # Create the heatmap
                    heatmap_fig = px.imshow(
                        heatmap_df,
                        color_continuous_scale=[[0, 'white'], [1, 'green']],
                        labels=dict(x="Year", y="Crop", color="Has Data"),
                        title=heatmap_title
                    )
                    
                    # Improve layout
                    heatmap_fig.update_layout(
                        xaxis=dict(tickmode='array', tickvals=list(heatmap_df.columns)),
                        coloraxis_showscale=False
                    )
                else:
                    heatmap_fig = go.Figure()
                    heatmap_fig.update_layout(title="Insufficient data for heatmap")
            
            else:
                # Case 3: Default view - Show Countries x Crops
                # Limit to top 20 countries and top 20 crops for readability if needed
                if len(filtered_df['country_code'].unique()) > 20 or len(filtered_df['crop'].unique()) > 20:
                    top_countries = filtered_df.groupby('country_code')['crop'].nunique().sort_values(ascending=False).head(20).index
                    top_crops = filtered_df.groupby('crop')['country_code'].nunique().sort_values(ascending=False).head(20).index
                    
                    heatmap_df = filtered_df[
                        filtered_df['country_code'].isin(top_countries) & 
                        filtered_df['crop'].isin(top_crops)
                    ]
                    
                    heatmap_title = "Data Coverage: Top 20 Countries × Top 20 Crops"
                else:
                    heatmap_df = filtered_df
                    heatmap_title = "Data Coverage: Countries × Crops"
                
                # Create a matrix of countries x crops showing the year span
                if not heatmap_df.empty:
                    pivot_df = heatmap_df.pivot_table(
                        index='country_name',
                        columns='crop',
                        values='year_count',
                        aggfunc='max',
                        fill_value=0
                    )
                    
                    # Create the heatmap
                    heatmap_fig = px.imshow(
                        pivot_df,
                        color_continuous_scale=px.colors.sequential.Viridis,
                        labels=dict(x="Crop", y="Country", color="Years of Data"),
                        title=heatmap_title
                    )
                    
                    # Improve layout
                    heatmap_fig.update_layout(
                        xaxis={'title': 'Crop'},
                        yaxis={'title': 'Country'},
                    )
                else:
                    heatmap_fig = go.Figure()
                    heatmap_fig.update_layout(title="Insufficient data for heatmap")
        else:
            heatmap_fig = go.Figure()
            heatmap_fig.update_layout(
                title="No data available for heatmap with selected filters"
            )
        
        # Create indicator availability figure
        if not filtered_df.empty:
            # Prepare data for bar graph
            indicator_data = {
                'Indicator': ['Area Planted', 'Area Harvested', 'Quantity Produced', 'Production'],
                'Available': [
                    filtered_df['has_area_planted'].mean() * 100,
                    filtered_df['has_area_harvested'].mean() * 100,
                    filtered_df['has_quantity'].mean() * 100,
                    filtered_df['has_production'].mean() * 100
                ]
            }
            
            indicator_df = pd.DataFrame(indicator_data)
            
            # Create bar chart
            indicator_fig = px.bar(
                indicator_df,
                x='Indicator',
                y='Available',
                title="Indicator Availability in Selected Data (%)",
                labels={'Available': 'Percentage Available (%)'},
                color='Indicator',
                text_auto='.1f',
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            
            indicator_fig.update_layout(yaxis_range=[0, 100])
        else:
            indicator_fig = go.Figure()
            indicator_fig.update_layout(
                title="No data available for indicator graph with selected filters"
            )
        
        # Summary statistics
        if not filtered_df.empty:
            summary_stats = html.Div([
                html.H4(f"Found {len(filtered_df)} records matching your criteria"),
                html.P(f"Countries: {filtered_df['country_code'].nunique()} | Crops: {filtered_df['crop'].nunique()}"),
                html.P(f"Earliest year: {filtered_df['year_min'].min()} | Latest year: {filtered_df['year_max'].max()} | Total year span: {filtered_df['year_max'].max() - filtered_df['year_min'].min() + 1} years")
            ])
        else:
            summary_stats = html.Div([
                html.H4("No data found matching your criteria"),
                html.P("Please adjust your filters to see results.")
            ])
        
        # Data table with pagination
        if not filtered_df.empty:
            # Prepare data for table - use all records
            table_df = filtered_df[['country_name', 'crop', 'year_range', 'seasonality', 'indicators_available']]
            
            # Create the data table with pagination
            table = dash_table.DataTable(
                columns=[{"name": col.replace('_', ' ').title(), "id": col} for col in table_df.columns],
                data=table_df.to_dict('records'),
                style_table={'overflowX': 'auto'},
                style_cell_conditional=[
                {'if': {'column_id': 'country_name'}, 'width': '18%'},
                {'if': {'column_id': 'crop'}, 'width': '20%'},
                {'if': {'column_id': 'year_range'}, 'width': '10%'},
                {'if': {'column_id': 'seasonality'}, 'width': '17%'},
                {'if': {'column_id': 'indicators_available'}, 'width': '35%'},
            ],
            style_cell={
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'whiteSpace': 'normal',
                'height': 'auto',
                'padding': '10px',
                'textAlign': 'left'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold',
                'textAlign': 'center'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ],
                page_size=15,  # Show 15 records per page
                page_action='native',  # Enable built-in pagination
                sort_action='native',  # Enable built-in sorting
                filter_action='native',  # Enable built-in filtering
            )
            
            data_table = html.Div([
                html.H5(f"Data Inventory ({len(table_df)} Records)"),
                table,
                html.P("Use the pagination controls to view more records. You can also sort by any column by clicking the header.")
            ])
        else:
            data_table = html.Div([
                html.H5("No data available for display"),
                html.P("Please adjust your filters to see results.")
            ])
        
        return map_fig, heatmap_fig, indicator_fig, summary_stats, data_table
    
    # Reset button callback
    @app.callback(
        [
            Output("country-dropdown", "value"),
            Output("crop-dropdown", "value"),
            Output("year-slider", "value"),
            Output("metrics-checklist", "value")
        ],
        [Input("reset-button", "n_clicks")]
    )
    def reset_filters(n_clicks):
        if n_clicks is None:
            raise dash.exceptions.PreventUpdate
        
        return (
            None,
            None,
            [int(min_year), int(max_year)],
            []
        )
    
    return app