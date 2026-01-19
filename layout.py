from dash import dcc, html
import data_loader
import constants

def create_layout(app):
    # Location filter
    metr_loc = dcc.Dropdown(
            id='location_filter',
            options=[{"label": loc, "value": loc} for loc in constants.SUBSCRIBER_LOCATIONS],
            value=[],
            placeholder="Select Location",
            multi=True,
            style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
        )

    # Year filter
    available_years = sorted(data_loader.df_cost['Year'].unique(), reverse=True)
    year_dropdown = dcc.Dropdown(
        id='year_filter',
        options=[{'label': y, 'value': y} for y in available_years],
        value=[available_years[0]] if available_years else [],
        placeholder="Select Year",
        multi=True,
        style={'width': '90%', 'marginTop': '10px', "marginLeft": "5%"}
    )

    # Month filter
    mtr_month = dcc.Dropdown(
            id='month_filter',
            options=[{"label": m, "value": m} for m in data_loader.run_time["Month"].unique()],
            value=[],
            placeholder="Select Month",
            multi=True,
            style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
        )

    # Generator dropdown (safe sort)
    gens = data_loader.run_time['Generator'].dropna().astype(str).unique().tolist()
    gens = sorted(gens, key=lambda x: x.lower())  # case-insensitive sort

    filter_list = data_loader.df_rc_melt['Filter_Type'].unique().tolist()

    gen_dropdown = dcc.Dropdown(
        id='generator_type',
        options=[{"label": gen, "value": gen} for gen in gens],
        value=[],
        placeholder="Select Generator Type",
        multi=True,
        style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
    )

    filter_dropdown = dcc.Dropdown(
        id='filter_type',
        options=[{"label": fil, "value": fil} for fil in filter_list],
        value=[],
        placeholder="Filter Type",
        multi=True,
        style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
    )

    return html.Div([
        html.Meta(name='viewport', content='width=device-width, initial-scale=1.0'),
    
        # Sidebar
        html.Div([
            html.Img(
                src=app.get_asset_url('images/Gracefield_logo.png'),
                className="logo",
                alt="Gracefield logo"
            ),
            year_dropdown,
            mtr_month,
            metr_loc,
            gen_dropdown,
            html.Div([filter_dropdown], id='filter-dropdown-container'),
            html.Button("Power Analytics", id="tab1-btn", className="tab-btn active-tab",
                    style={"marginLeft": "1.5rem", "marginTop": "4rem"}),
            html.Button("Operations", id="tab2-btn", className="tab-btn",
                    style={"marginLeft": "1.5rem", "marginTop": "4rem"})
        ], id="sidebar", className="sidebar"),
    
        # Main Content
        html.Div([
            # Header section for KPIs
            html.Div([
                html.H2("Power Dashboard", className="title", style={'textAlign': 'left'}),
                # KPIs  
                html.Div([html.Div("💼", className="kpi-icon"), html.Div([html.P("Revenue", className="kpi-label"), html.H3(id="total_revenue", className="kpi-value")], className="kpi-text")], className="kpi-card"),
                html.Div([html.Div("⏱️", className="kpi-icon"), html.Div([html.P("Operated Hours", className="kpi-label"), html.H3(id="operated_hours", className="kpi-value")], className="kpi-text")], className="kpi-card"),
                html.Div([html.Div("⏸️", className="kpi-icon"), html.Div([html.P("Unplanned Outage", className="kpi-label"), html.H3(id="unplanned_outage", className="kpi-value")], className="kpi-text")], className="kpi-card"),
                html.Div([html.Div("🧾", className="kpi-icon"), html.Div([html.P("Total Cost", className="kpi-label"), html.H3(id="total_cost_kpi", className="kpi-value")], className="kpi-text")], className="kpi-card"),
                html.Div([html.Div("📈", className="kpi-icon"), html.Div([html.P("%Revenue Change", className="kpi-label"), html.H3(id="revenue_change_kpi", className="kpi-value")], className="kpi-text")], className="kpi-card"),
            ], className="header", style={'display': 'flex', 'gap': '20px', 'alignItems': 'center', 'flexWrap': 'wrap'}),

            # Tab 1: Power Analytics
            html.Div([
                html.Div([dcc.Graph(id='trans_chart', className='trans-chart', config={"responsive": True}, style={"width": "100%", "height": "100%", "flex": "1 1 auto"})], className="card-1"),
                html.Div([dcc.Graph(id='cost_chart', config={"responsive": True}, style={"width": "100%", "height": "100%", "flex": "1 1 auto"}, className='cost-chart')], className="card-4"),
                html.Div([dcc.Graph(id='revenue_cost_chart', config={"responsive": True}, style={"width": "100%", "height": "100%", "flex": "1 1 auto"}, className='consumption-chart')], className="card-2"),
            ], id="tab-1", className="section"),

            # Tab 2: Operations
            html.Div([
                html.Div([
                    html.Div(id='fuel_change_kpi', style={'textAlign': 'center', 'paddingBottom': '10px', 'fontWeight': 'bold', 'fontSize': '1.1em'}),
                    dcc.Graph(id='fuel_chart', className='fuel-chart', config={"responsive": True}, style={"width": "100%", "height": "100%", "flex": "1 1 auto"})
                ], className="card-1"),
                html.Div([dcc.Graph(id='runtime_chart', className='runtime-chart', config={"responsive": True}, style={"width": "100%", "height": "100%", "flex": "1 1 auto"})], className="card-5"),
                html.Div([
                    dcc.Graph(id='stock_chart', className='stock-chart', config={"responsive": True}, style={"width": "100%", "height": "100%", "flex": "1 1 auto"})
                ], className="card-3"),
                html.Div([dcc.Graph(id='downtime_chart', className='downtime-chart', config={"responsive": True}, style={"width": "100%", "height": "100%", "flex": "1 1 auto"})], className="card-4"),
            ], id="tab-2", className="section", style={"display": "none"}),
        
            dcc.Interval(id='data-refresh-interval', interval=300000, n_intervals=0),
        ], className="main-content")
    ], className="app-grid")
