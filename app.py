from dash import dash_table, dash, html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sb
import pandas as pd
from dash import Dash, dcc, html, Input, Output, callback_context
import os
import warnings
import calendar
from collections import Counter
import threading
from datetime import datetime, timedelta
import sys
import webbrowser

warnings.filterwarnings('ignore')

# --- Global Variables ---
data_lock = threading.Lock()
last_refresh_time = None
REFRESH_INTERVAL = 300  # 5 minutes in seconds

def load_all_data():
    """Load and process data from Google Sheets with thread safety."""
    global df_meter, df_cost, df_cost_2025, df_downTime, run_time, df_agg
    global df_supplied, df_stock, df_rc, df_rc_melt, power_df, last_refresh_time
    
    with data_lock:
        try:
            # Check if we need to refresh (5-minute interval)
            current_time = datetime.now()
            if (last_refresh_time is None or 
                (current_time - last_refresh_time).total_seconds() >= REFRESH_INTERVAL):
                
                print("Refreshing data from source...")
                
                url = "https://docs.google.com/spreadsheets/d/1LfdWF1pzfC8PGwD-pMgzHw8JIZtll74W8-39vNsKgGA/edit?usp=sharing"

                sheet_id = "1LfdWF1pzfC8PGwD-pMgzHw8JIZtll74W8-39vNsKgGA"
                excel_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
                df = pd.ExcelFile(excel_url)

                # --- Meter Data ---
                df_meter = df.parse(0)
                if 'Total Revenue' in df_meter.columns:
                    df_meter['Total Revenue'] = df_meter['Total Revenue'].astype(str).str.replace(',', '', regex=False)
                    df_meter['Total Revenue'] = df_meter['Total Revenue'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                    df_meter['Total Revenue'] = pd.to_numeric(df_meter['Total Revenue'], errors='coerce').fillna(0)

                if 'Year' in df_meter.columns:
                    df_meter['Year'] = df_meter['Year'].astype(str).str.replace(r'\.0', '', regex=True)
                elif 'Date' in df_meter.columns:
                    df_meter['Date'] = pd.to_datetime(df_meter['Date'])
                    df_meter['Year'] = df_meter['Date'].dt.strftime('%Y')

                month_order = ["January","February","March","April","May","June","July","August","September","October","November","December"]
                if 'Month' in df_meter.columns:
                    df_meter['Month'] = df_meter['Month'].astype(str).str.strip()
                df_meter['Month'] = pd.Categorical(df_meter['Month'], categories=month_order, ordered=True)

                # --- Cost Breakdown ---
                df_cost = df.parse(1)
                if 'Amount (NGN)' in df_cost.columns:
                    df_cost['Amount (NGN)'] = df_cost['Amount (NGN)'].astype(str).str.replace(',', '', regex=False)
                    df_cost['Amount (NGN)'] = df_cost['Amount (NGN)'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                    df_cost['Amount (NGN)'] = pd.to_numeric(df_cost['Amount (NGN)'], errors='coerce').fillna(0)

                df_cost['Generator'].replace(['new 80kva', 'both 80kva', 'old 80kva', 'new 200kva', '55Kva'],
                                         ['80kva', '80kva', '80kva',  '200kva', '55kva' ], inplace= True)

                # Normalize generator names to lowercase to ensure matching (e.g. '80KVA' -> '80kva')
                if 'Generator' in df_cost.columns:
                    df_cost['Generator'] = df_cost['Generator'].astype(str).str.strip().str.lower()

                if 'Year' in df_cost.columns:
                    df_cost['Year'] = df_cost['Year'].astype(str).str.replace(r'\.0', '', regex=True)
                elif 'Date' in df_cost.columns:
                    df_cost['Date'] = pd.to_datetime(df_cost['Date'])
                    df_cost['Year'] = df_cost['Date'].dt.strftime('%Y')
                
                if 'Month' in df_cost.columns:
                    df_cost['Month'] = df_cost['Month'].astype(str).str.strip()
                elif 'Date' in df_cost.columns:
                    if df_cost['Date'].dtype == object:
                        df_cost['Date'] = pd.to_datetime(df_cost['Date'])
                    df_cost['Month'] = df_cost['Date'].dt.strftime('%B')

                df_cost.drop(columns=['id'], inplace=True, errors='ignore')
                df_cost.reset_index(drop= True, inplace=True)
                
                df_cost_2025 = df_cost.copy()

                # --- Downtime ---
                df_downTime = df.parse(2)
                df_downTime = df_downTime.sort_values(by='Duration_Hours', ascending=False)
                df_downTime['Generator'] = df_downTime['Generator'].replace('88kva', '80kva')

                # Normalize generator names
                if 'Generator' in df_downTime.columns:
                    df_downTime['Generator'] = df_downTime['Generator'].astype(str).str.strip().str.lower()

                if 'Year' in df_downTime.columns:
                    df_downTime['Year'] = df_downTime['Year'].astype(str).str.replace(r'\.0', '', regex=True)
                elif 'Date' in df_downTime.columns:
                    df_downTime['Date'] = pd.to_datetime(df_downTime['Date'], errors='coerce')
                    df_downTime['Year'] = df_downTime['Date'].dt.strftime('%Y')
                
                if 'Month' in df_downTime.columns:
                    df_downTime['Month'] = df_downTime['Month'].astype(str).str.strip()
                elif 'Date' in df_downTime.columns:
                     df_downTime['Month'] = df_downTime['Date'].dt.strftime('%B')

                df_downTime["Month"] = pd.Categorical(
                    df_downTime["Month"],
                    categories=month_order,
                    ordered=True
                )
                group_cols = ["Year", "Month", "Generator"] if 'Year' in df_downTime.columns else ["Month", "Generator"]
                df_downTime = df_downTime.groupby(group_cols, as_index=False)["Duration_Hours"].sum()

                # --- Runtime ---
                run_time = df.parse(4)
                if 'Year' in run_time.columns:
                    run_time['Year'] = run_time['Year'].astype(str).str.replace(r'\.0', '', regex=True)
                elif 'Date' in run_time.columns:
                    run_time['Date'] = pd.to_datetime(run_time['Date'])
                    run_time['Year'] = run_time['Date'].dt.strftime('%Y')
                
                if 'Month' in run_time.columns:
                    run_time['Month'] = run_time['Month'].astype(str).str.strip()
                elif 'Date' in run_time.columns:
                    if run_time['Date'].dtype == object:
                        run_time['Date'] = pd.to_datetime(run_time['Date'])
                    run_time['Month'] = run_time['Date'].dt.strftime('%B')
                
                if 'Day' not in run_time.columns and 'Date' in run_time.columns:
                    if run_time['Date'].dtype == object:
                        run_time['Date'] = pd.to_datetime(run_time['Date'])
                    run_time['Day'] = run_time['Date'].dt.strftime('%A')
                    
                run_time['Generator'].replace(['20KVA', '200KVA', '80KVA', '55KVA'], ['20kva', '200kva', '80kva', '55kva'], inplace = True)
                
                # Normalize generator names
                if 'Generator' in run_time.columns:
                    run_time['Generator'] = run_time['Generator'].astype(str).str.strip().str.lower()

                df_agg = run_time.groupby(['Year', 'Month', 'Generator'], as_index=False)['Hours Operated'].sum()
                df_agg['Month'] = pd.Categorical(df_agg['Month'], categories=month_order, ordered=True)
                df_agg = df_agg.sort_values(by='Month')

                # --- Fuel Supplied ---
                df_supplied = df.parse(3)

                if 'Year' in df_supplied.columns:
                    df_supplied['Year'] = df_supplied['Year'].astype(str).str.replace(r'\.0', '', regex=True)
                elif 'Date' in df_supplied.columns:
                    df_supplied['Date'] = pd.to_datetime(df_supplied['Date'])
                    df_supplied['Year'] = df_supplied['Date'].dt.strftime('%Y')

                if 'Month' in df_supplied.columns:
                    df_supplied['Month'] = df_supplied['Month'].astype(str).str.strip()
                elif 'Date' in df_supplied.columns:
                    if df_supplied['Date'].dtype == object:
                        df_supplied['Date'] = pd.to_datetime(df_supplied['Date'])
                    df_supplied['Month'] = df_supplied['Date'].dt.strftime('%B')

                
                # --- Stock ---
                df_stock = df.parse(5)
                if 'Year' in df_stock.columns:
                    df_stock['Year'] = df_stock['Year'].astype(str).str.replace(r'\.0', '', regex=True)
                    if 'Month' in df_stock.columns:
                        df_stock['Month'] = df_stock['Month'].astype(str).str.strip()
                else:
                    df_stock['Date_Obj'] = pd.to_datetime(df_stock['Month'])
                    df_stock['Month'] = df_stock['Date_Obj'].dt.strftime('%B')
                    df_stock['Year'] = df_stock['Date_Obj'].dt.strftime('%Y')
                
                if 'Generator_Size' in df_stock.columns:
                    df_stock['Generator_Size'] = df_stock['Generator_Size'].astype(str).str.strip().str.lower()

                df_rc_melt = df_stock.copy()

                # --- Power Transaction ---
                power_df = df.parse(6)
                if 'Amount' in power_df.columns:
                    power_df['Amount'] = power_df['Amount'].astype(str).str.replace(',', '', regex=False)
                    power_df['Amount'] = power_df['Amount'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                    power_df['Amount'] = pd.to_numeric(power_df['Amount'], errors='coerce').fillna(0)

                try:
                    power_df['Transaction Date'] = power_df['Transaction Date'].astype(str)
                    power_df['Transaction Date'] = pd.to_datetime(power_df['Transaction Date'], dayfirst=True, errors='coerce')
                    
                    if not pd.api.types.is_datetime64_any_dtype(power_df['Transaction Date']):
                        power_df['Transaction Date'] = power_df['Transaction Date'].astype(str)
                        power_df['Transaction Date'] = pd.to_datetime(power_df['Transaction Date'], dayfirst=True, errors='coerce')
                    
                    power_df = power_df.dropna(subset=['Transaction Date'])
                except Exception:
                    pass

                # Extract month name for easier filtering in callback (keep all months)
                if 'Year' in power_df.columns:
                    power_df['Year'] = power_df['Year'].astype(str).str.replace(r'\.0', '', regex=True)
                elif 'Transaction Date' in power_df.columns:
                    power_df['Year'] = power_df['Transaction Date'].dt.strftime('%Y')

                if 'Month' not in power_df.columns and 'Transaction Date' in power_df.columns:
                    power_df['Month'] = power_df['Transaction Date'].dt.strftime('%B')

                power_df.reset_index(drop=True, inplace=True)
                
                last_refresh_time = current_time
                print("Data refresh completed successfully")
                
        except Exception as e:
            print(f"Error refreshing data: {e}") 

# Initial data load
load_all_data()

# --- Interactivity Components ---

# Define subscriber and gravitas locations
subscriber_locations = [
    'Tuck-shop',
    'HELIUM',
    'NBIC 1',
    'NBIC 2',
    'Gravitas Canteen',
    'Cedar A',
    'Cedar B',
    'Rosewood A',
    'Rosewood B',
    'DIC',
    'Western Lodge'
]

gravitas_revenue_sources = [
    'Gravitas New Meter',
    'Engineering Yard',
    'Providus',
    '9mobile'
]


# Location filter
metr_loc = dcc.Dropdown(
        id='location_filter',
        options=[{"label": loc, "value": loc} for loc in subscriber_locations],
        value=[],
        placeholder="Select Location",
        multi=True,
        style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
    )

# Year filter
available_years = sorted(df_cost['Year'].unique(), reverse=True)
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
        options=[{"label": m, "value": m} for m in run_time["Month"].unique()],
        value=[],
        placeholder="Select Month",
        multi=True,
        style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
    )

# Generator dropdown (safe sort)
gens = run_time['Generator'].dropna().astype(str).unique().tolist()
gens = sorted(gens, key=lambda x: x.lower())  # case-insensitive sort


filter = df_rc_melt['Filter_Type'].unique().tolist()


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
    options=[{"label": fil, "value": fil} for fil in filter],
    value=[],
    placeholder="Filter Type",
    multi=True,
    style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
)


# Graph components
revCostChart = dcc.Graph(id='revenue_cost_chart', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"}, className='consumption-chart')

consumpLine = dcc.Graph(id='consumption_line', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"}, className='consumption-line')

costChart = dcc.Graph(id='cost_chart', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"}, className='cost-chart')
costPie = dcc.Graph(id='cost_pie', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"}, className='cost-pie')

fuelChart = dcc.Graph(id='fuel_chart', className='fuel-chart', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"})

downtimeChart = dcc.Graph(id='downtime_chart', className='downtime-chart', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"})

stockChart = dcc.Graph(id='stock_chart', className='stock-chart', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"})

runtimeChart = dcc.Graph(id='runtime_chart', className='runtime-chart', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"})

transChart = dcc.Graph(id='trans_chart', className='trans-chart', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"})


# Determine assets folder path based on whether running as source or frozen executable
if getattr(sys, 'frozen', False):
    # Running as compiled executable (PyInstaller unpacks to sys._MEIPASS)
    assets_folder = os.path.join(sys._MEIPASS, 'assets')
else:
    # Running from source
    assets_folder = 'assets'

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], assets_folder=assets_folder)
server = app.server
app.config.suppress_callback_exceptions = True

# --- App Layout ---
app.layout = html.Div([
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
            html.Div([
                html.Div("💼", className="kpi-icon"),
                html.Div([
                    html.P("Revenue", className="kpi-label"),
                    html.H3(id="total_revenue", className="kpi-value"),
                ], className="kpi-text")
            ], className="kpi-card"),

            html.Div([
                html.Div("⏱️", className="kpi-icon"),
                html.Div([
                    html.P("Operated Hours", className="kpi-label"),
                    html.H3(id="operated_hours", className="kpi-value")
                ], className="kpi-text")
            ], className="kpi-card"),

            html.Div([
                html.Div("⏸️", className="kpi-icon"),
                html.Div([
                    html.P("Unplanned Outage", className="kpi-label"),
                    html.H3(id="unplanned_outage", className="kpi-value")
                ], className="kpi-text")
            ], className="kpi-card"),

            html.Div([
                html.Div("🧾", className="kpi-icon"),
                html.Div([
                    html.P("Total Cost", className="kpi-label"),
                    html.H3(id="total_cost_kpi", className="kpi-value")
                ], className="kpi-text")
            ], className="kpi-card"),

            html.Div([
                html.Div("📈", className="kpi-icon"),
                html.Div([
                    html.P("% Change in Revenue", className="kpi-label"),
                    html.H3(id="revenue_change_kpi", className="kpi-value")
                ], className="kpi-text")
            ], className="kpi-card"),
        ], className="header", style={'display': 'flex', 'gap': '20px', 'alignItems': 'center', 'flexWrap': 'wrap'}),

        # Tab 1: Power Analytics
        html.Div([
            html.Div([transChart], className="card-1"),
            html.Div([costChart], className="card-4"),
            html.Div([revCostChart], className="card-2"),
        ], id="tab-1", className="section"),

        # Tab 2: Operations
        html.Div([
            html.Div([
                html.Div(id='fuel_change_kpi', style={'textAlign': 'center', 'paddingBottom': '10px', 'fontWeight': 'bold', 'fontSize': '1.1em'}),
                fuelChart
            ], className="card-1"),
            html.Div([runtimeChart], className="card-5"),
            html.Div([
                stockChart
            ], className="card-3"),
            html.Div([downtimeChart], className="card-4"),
        ], id="tab-2", className="section", style={"display": "none"}),
        
        dcc.Interval(id='data-refresh-interval', interval=300000, n_intervals=0),
    ], className="main-content")
], className="app-grid")



# --- Callbacks ---
@app.callback(
    [
        Output('tab-1', 'style'),
        Output('tab-2', 'style'),
        Output('tab1-btn', 'className'),
        Output('tab2-btn', 'className'),
        Output('filter-dropdown-container', 'style'),
    ],
    [
        Input('tab1-btn', 'n_clicks'),
        Input('tab2-btn', 'n_clicks'),
    ],
    prevent_initial_call=False
)
def switch_tabs(tab1_clicks, tab2_clicks):
    ctx = callback_context
    if not ctx.triggered:
        # Initial load: show tab-1
        return {'display': 'flex'}, {'display': 'none'}, 'tab-btn active-tab', 'tab-btn', {'display': 'none'}
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'tab2-btn':
        return {'display': 'none'}, {'display': 'flex'}, 'tab-btn', 'tab-btn active-tab', {'display': 'block'}
    else:
        return {'display': 'flex'}, {'display': 'none'}, 'tab-btn active-tab', 'tab-btn', {'display': 'none'}

@app.callback(
    [
        Output('revenue_cost_chart', 'figure'),
        Output('trans_chart', 'figure'),
        Output('total_revenue', 'children'),
        Output('operated_hours', 'children'),
        Output('unplanned_outage', 'children'),
        Output('total_cost_kpi', 'children'),
        Output('revenue_change_kpi', 'children'),
        Output('cost_chart', 'figure'),
        Output('fuel_chart', 'figure'),
        Output('fuel_change_kpi', 'children'),
        Output('downtime_chart', 'figure'),
        Output('stock_chart', 'figure'),
        Output('runtime_chart', 'figure'),
    ],
    [
        Input('location_filter', 'value'),
        Input('month_filter', 'value'),
        Input('year_filter', 'value'),
        Input('generator_type', 'value'),
        Input('filter_type', 'value'),
        Input('data-refresh-interval', 'n_intervals'),
    ]
   
)
def update_chart(selected_locations, selected_months, selected_years, selected_generators, selected_filter, n_intervals):
    # Ensure data is fresh
    load_all_data()
    
    # Create thread-safe copies of the data for this callback
    with data_lock:
        local_df_meter = df_meter.copy()
        local_df_cost_2025 = df_cost_2025.copy()
        local_power_df = power_df.copy()
        local_df_supplied = df_supplied.copy()
        local_df_downTime = df_downTime.copy()
        local_df_rc_melt = df_rc_melt.copy()
        local_df_agg = df_agg.copy()
        local_df_cost = df_cost.copy()
        local_run_time = run_time.copy()
        
    # === Apply Year Filter ===
    if selected_years:
        # Filter all dataframes by selected years
        if 'Year' in local_df_cost_2025.columns:
            local_df_cost_2025 = local_df_cost_2025[local_df_cost_2025['Year'].isin(selected_years)]
        if 'Year' in local_power_df.columns:
            local_power_df = local_power_df[local_power_df['Year'].isin(selected_years)]
        if 'Year' in local_df_supplied.columns:
            local_df_supplied = local_df_supplied[local_df_supplied['Year'].isin(selected_years)]
        if 'Year' in local_df_downTime.columns:
            local_df_downTime = local_df_downTime[local_df_downTime['Year'].isin(selected_years)]
        if 'Year' in local_df_rc_melt.columns:
            local_df_rc_melt = local_df_rc_melt[local_df_rc_melt['Year'].isin(selected_years)]
        if 'Year' in local_df_agg.columns:
            local_df_agg = local_df_agg[local_df_agg['Year'].isin(selected_years)]
        if 'Year' in local_df_meter.columns:
            local_df_meter = local_df_meter[local_df_meter['Year'].isin(selected_years)]

    meter_to_name = {
        23220035721: "Rosewood A",
        23220035788: "Rosewood B",
        4293684496:  "Cedar A",
        4293682284:  "Cedar B",
        4293683936:  "NBIC 1",
        4293682789:  "NBIC 2",
        4293682193:  "Head Office",
        4293683571:  "Engineering Yard",
        4293683993:  "HELIUM",
        4293682201:  "DIC",
        120230672145: "Tuckshop Water",
        4293684066: "Tuck-shop"
    }
        
    filtered_meter = local_df_meter.copy()

    if selected_locations:
        filtered_meter = filtered_meter[filtered_meter["Location"].isin(selected_locations)]

    if selected_months:
        filtered_meter = filtered_meter[filtered_meter["Month"].isin(selected_months)]

    filtered_meter['Total Revenue'] = pd.to_numeric(filtered_meter['Total Revenue'], errors='coerce').fillna(0)
    
    gravitas_partner = round(filtered_meter.loc[
        filtered_meter['Location'].isin(['9mobile', 'Providus', 'Western Lodge']), "Total Revenue"
    ].sum(), 2)

    gravitas_subscriber = round(filtered_meter.loc[
        filtered_meter['Location'] == 'Canteen', "Total Revenue"
    ].sum(), 2)
    
    # --- Brand Colors ---
    GRACEFIELD_GOLD     = "#C7A64F"
    GRACEFIELD_DARK     = "#2C3E50"
    GRACEFIELD_Green     = "#166347"
    GRACEFIELD_SKY      = "#4A90E2"
    GRACEFIELD_ORANGE   = "#E67E22"
   

    brand_colors = [GRACEFIELD_Green, GRACEFIELD_GOLD, GRACEFIELD_DARK, GRACEFIELD_SKY, GRACEFIELD_ORANGE]
    
    # === Revenue & Cost Calculation ===
    revenue_from_trans = local_power_df.copy()
    revenue_from_trans['Amount'] = pd.to_numeric(revenue_from_trans['Amount'], errors='coerce').fillna(0)
    
    # Apply year and month filters to transaction data
    if selected_years:
        revenue_from_trans = revenue_from_trans[revenue_from_trans['Year'].isin(selected_years)]
    if selected_months:
        revenue_from_trans = revenue_from_trans[revenue_from_trans['Month'].isin(selected_months)]
    
    monthly_revenue = revenue_from_trans.groupby('Month')['Amount'].sum().reset_index()
    monthly_revenue.columns = ['Month', 'Revenue']

    # Add meter revenue to transaction revenue
    meter_rev_df = local_df_meter.copy()
    meter_rev_df['Total Revenue'] = pd.to_numeric(meter_rev_df['Total Revenue'], errors='coerce').fillna(0)
    
    # Apply year and month filters to meter data
    if selected_years:
        meter_rev_df = meter_rev_df[meter_rev_df['Year'].isin(selected_years)]
    if selected_months:
        meter_rev_df = meter_rev_df[meter_rev_df['Month'].isin(selected_months)]
    
    monthly_meter_revenue = meter_rev_df.groupby('Month')['Total Revenue'].sum().reset_index()
    monthly_meter_revenue.columns = ['Month', 'Meter_Revenue']

    # Combine transaction revenue with the additional meter-based revenue
    if not monthly_meter_revenue.empty:
        monthly_revenue = monthly_revenue.merge(monthly_meter_revenue, on='Month', how='outer')
        monthly_revenue['Revenue'] = monthly_revenue['Revenue'].fillna(0) + monthly_revenue['Meter_Revenue'].fillna(0)
        monthly_revenue = monthly_revenue[['Month', 'Revenue']]

    # 2. Cost: Sum all costs (Fuel + Maintenance)
    cost_by_month = local_df_cost_2025.copy()
    if selected_months:
        cost_by_month = cost_by_month[cost_by_month['Month'].isin(selected_months)]
    if selected_generators:
        cost_by_month = cost_by_month[cost_by_month['Generator'].isin(selected_generators)]

    # Convert to numeric
    cost_by_month['Amount (NGN)'] = pd.to_numeric(cost_by_month['Amount (NGN)'], errors='coerce').fillna(0)

    monthly_cost = cost_by_month.groupby('Month')['Amount (NGN)'].sum().reset_index()
    monthly_cost.columns = ['Month', 'Total_Cost']

    # 3. Merge Revenue and Cost
    margin_data = monthly_revenue.merge(monthly_cost, on='Month', how='outer').fillna(0)

    # Calculate Gross Margin
    margin_data['Profit'] = margin_data['Revenue'] - margin_data['Total_Cost']
    margin_data['Margin_Percent'] = (margin_data['Profit'] / margin_data['Revenue'] * 100).fillna(0)
    margin_data['Margin_Label'] = margin_data['Margin_Percent'].apply(lambda x: 'Gross Margin' if x >= 0 else 'Gross Margin')

    # Sort by month order
    month_order = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    margin_data['Month'] = pd.Categorical(margin_data['Month'], categories=month_order, ordered=True)
    margin_data = margin_data.sort_values('Month')

    # === Revenue vs Cost Chart ===
    fig_margin = make_subplots(specs=[[{"secondary_y": True}]])

    # Add Revenue bars
    fig_margin.add_trace(
        go.Bar(
            x=margin_data['Month'],
            y=margin_data['Revenue'],
            name='Revenue',
            marker_color=GRACEFIELD_GOLD,
            text=margin_data['Revenue'],
            texttemplate='₦%{text:,.0f}',
            textposition='outside',
            textfont=dict(size=10),
            hovertemplate='<b>Revenue</b><br>₦%{y:,.0f}<extra></extra>'
        ),
        secondary_y=False)
    # Add Cost bars
    fig_margin.add_trace(
        go.Bar(
            x=margin_data['Month'],
            y=margin_data['Total_Cost'],
            name='Total Cost',
            marker_color=GRACEFIELD_DARK,
            text=margin_data['Total_Cost'],
            texttemplate='₦%{text:,.0f}',
            textposition='outside',
            textfont=dict(size=10),
            hovertemplate='<b>Total Cost</b><br>₦%{y:,.0f}<extra></extra>'
        ),
        secondary_y=False
    )

    # Add Profit Margin % line (secondary y-axis)
    fig_margin.add_trace(
        go.Scatter(
            x=margin_data['Month'],
            y=margin_data['Margin_Percent'],
            name='Gross Margin %',
            mode='lines+markers+text',
            line=dict(color="red", width=3, dash='dash'),
            marker=dict(size=10, symbol='diamond'),
            text=margin_data['Margin_Percent'],
            texttemplate='%{text:.1f}%',
            textposition='top center',
            textfont=dict(size=11, color='red'),
            customdata=margin_data['Margin_Label'],
            hovertemplate='<b>%{customdata}</b><br>%{y:.1f}%<extra></extra>'
        ), secondary_y=True
    )
    # Update layout
    fig_margin.update_layout(
        title=dict(
            text='💰 Revenue vs Cost with Gross Margin',
            font=dict(size=14, color='#111827', family='Arial Black'),
            x=0.5,
            xanchor='center',
            pad=dict(t=10, b=20)
        ),
        barmode='group',
        hovermode='x unified',
        template="plotly_white",
        margin=dict(t=60, b=60, l=60, r=120),
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(0,0,0,0)',
            borderwidth=0
        )
    )

    # Set y-axes titles
    fig_margin.update_yaxes(title_text="Amount (₦)", secondary_y=False)
    fig_margin.update_yaxes(title_text="Gross Margin (%)", secondary_y=True)

    # Rotate x-axis labels
    fig_margin.update_xaxes(tickangle=-45)

    # --- Transactions Trend Chart ---
    chart_df = local_power_df.copy()

    if selected_months:
        months_selected = selected_months if isinstance(selected_months, list) else [selected_months]
        chart_df = chart_df[chart_df['Month'].isin(months_selected)]

    # Clean addresses
    meter_to_name_str = {str(k): v for k, v in meter_to_name.items()}
    chart_df['Meter Number Str'] = chart_df['Meter Number'].astype(str).str.replace(r'\.0$', '', regex=True)
    chart_df['Resident Address'] = chart_df['Meter Number Str'].map(meter_to_name_str).fillna(chart_df['Resident Address'])

    # Exclude non-subscriber locations for trend analysis
    exclude_locations = ['Engineering Yard', 'Head Office', 'Gravitas New Meter', 'Providus', '9mobile', '9 mobile', 'Western Lodge']
    chart_df = chart_df[~chart_df['Resident Address'].isin(exclude_locations)]

    # Filter by selected location/address
    if selected_locations:
        locations_selected = selected_locations if isinstance(selected_locations, list) else [selected_locations]
        chart_df = chart_df[chart_df['Resident Address'].isin(locations_selected)]

    # Combine NBIC 1 and NBIC 2
    chart_df['Resident Address'] = chart_df['Resident Address'].astype(str).str.replace(r'(?i)NBIC\s*[12]', 'NBIC', regex=True).str.strip()

    # Group by Month and Address
    if not chart_df.empty:
        # Identify top 5 locations by revenue
        top_5_locations = chart_df.groupby('Resident Address')['Amount'].sum().nlargest(5).index

        top_locations_df = chart_df[chart_df['Resident Address'].isin(top_5_locations)]

        address_monthly = top_locations_df.groupby(['Month', 'Resident Address'], as_index=False)['Amount'].sum()
        
        # Ensure months are in correct order for plotting
        month_order = ["January","February","March","April","May","June","July","August","September","October","November","December"]
        address_monthly['Month'] = pd.Categorical(address_monthly['Month'], categories=month_order, ordered=True)
        address_monthly = address_monthly.sort_values('Month')
        
        # Create a complete DataFrame with all months for each top location
        all_months_df = pd.DataFrame({
            'Month': month_order,
            'key': 1
        })
        all_locations_df = pd.DataFrame({'Resident Address': top_5_locations, 'key': 1})
        
        # Merge to get all combinations of month and top locations
        full_trend_df = pd.merge(all_months_df, all_locations_df, on='key').drop('key', axis=1)
        address_monthly = pd.merge(full_trend_df, address_monthly, on=['Month', 'Resident Address'], how='left').fillna(0)

        # Create line chart
        fig_trans = px.line(
            address_monthly,
            x='Month',
            y='Amount',
            color='Resident Address',
            markers=True,
            labels={'Amount': 'Revenue (₦)', 'Resident Address': 'Subscriber', 'Month': 'Month'},
            color_discrete_sequence=brand_colors
        )
        
        # Style the line traces
        fig_trans.update_traces(line=dict(width=2.5), marker=dict(size=8))
        
        fig_trans.update_layout(
            title=dict(text='💰 Top 5 Subscribers - Revenue Trend', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
            autosize=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=28, b=8, l=20, r=120),
            xaxis_title='',
            yaxis_title='Revenue (₦)',
            template="plotly_white",
            legend=dict(
                orientation='v',
                x=1.02,
                xanchor='left',
                y=1,
                yanchor='top',
                font=dict(size=10),
                bgcolor='rgba(0,0,0,0)',
                borderwidth=0,
                title=dict(text='Subscriber')
            )
        )
        
        fig_trans.update_xaxes(tickangle=-45)
    else:
        # Empty chart if no data
        fig_trans = px.line(title="No transaction data available")
        fig_trans.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=28, b=8, l=20, r=20)
        )

    # --- Total Revenue KPI ---
    # Calculate total revenue from meter readings and transaction data
    meter_rev_df = df_meter.copy()
    meter_rev_df['Total Revenue'] = pd.to_numeric(meter_rev_df['Total Revenue'], errors='coerce').fillna(0)
    
    if selected_years:
        meter_rev_df = meter_rev_df[meter_rev_df['Year'].isin(selected_years)]
    if selected_months:
        meter_rev_df = meter_rev_df[meter_rev_df['Month'].isin(selected_months)]
        
    total_meter_revenue = meter_rev_df['Total Revenue'].sum()

    # Calculate transaction revenue
    power_rev_df = power_df.copy()
    power_rev_df['Amount'] = pd.to_numeric(power_rev_df['Amount'], errors='coerce').fillna(0)
    
    if selected_years:
        power_rev_df = power_rev_df[power_rev_df['Year'].isin(selected_years)]
    
    if selected_months:
        power_rev_df = power_rev_df[power_rev_df['Month'].isin(selected_months)]
    
    total_power_revenue = power_rev_df['Amount'].sum()
    total_revenue_value = total_meter_revenue + total_power_revenue
    totalRevenue = f"₦{total_revenue_value:,.0f}"

    # Prepare filtered data for detailed table calculations (for pivot table and cost breakdown)
    table_df = local_power_df.copy()
    table_df['Resident Address'] = table_df['Meter Number'].map(meter_to_name).fillna(table_df['Resident Address'])
    table_df['Amount'] = pd.to_numeric(table_df['Amount'], errors='coerce').fillna(0)
    
    # Apply filters only to the table/pivot data
    if selected_months:
        table_df = table_df[table_df['Month'].isin(selected_months)]
    if selected_locations:
        table_df = table_df[table_df['Resident Address'].isin(selected_locations)]
    
    table_df['Meter Name'] = table_df['Meter Number'].map(meter_to_name)
    if not table_df.empty:
        pivot_list = []
        for col in table_df['Resident Address'].unique():
            temp = pd.pivot_table(
                table_df[table_df["Resident Address"] == col],
                values="Amount",
                index="Meter Number",
                columns="Resident Address",
                aggfunc="sum"
            )
            pivot_list.append(temp)
        
        pivot = pd.concat(pivot_list, axis=0).fillna('-').reset_index()
    else:
        pivot = pd.DataFrame(columns=['Meter Number'])

    
     # === Cost Breakdown Chart ===
    filtered_cost = local_df_cost_2025.copy()
    # Format pivot table values to 2 decimal places
    cols_to_format = [col for col in pivot.columns if col != "Meter Number"]
    pivot[cols_to_format] = pivot[cols_to_format].applymap(
        lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x
    )

    if selected_generators:
        filtered_cost = filtered_cost[filtered_cost["Generator"].isin(selected_generators)]
    if selected_months:
        filtered_cost = filtered_cost[filtered_cost["Month"].isin(selected_months)]
    df_table = pd.DataFrame(pivot.to_dict('records'))

    # Calculate Maintenance Costs
    filtered_cost['Amount (NGN)'] = pd.to_numeric(filtered_cost['Amount (NGN)'], errors='coerce').fillna(0)
    maintenance = filtered_cost[filtered_cost['Type of Activity'].str.contains('maintenance', case=False, na=False)]
    
    routine_cost = maintenance[
        maintenance['Type of Activity'].str.contains('Routine', case=False, na=False)
    ]['Amount (NGN)'].sum()

    def safe_sum(col):
        """Sum numeric values in a dataframe column, treating '-' as 0"""
        if col in df_table.columns:
            return pd.to_numeric(df_table[col].replace('-', 0), errors='coerce').sum()
        return 0

    corrective_cost = maintenance[
        maintenance['Type of Activity'].str.contains('Corrective', case=False, na=False)
    ]['Amount (NGN)'].sum()
    gho = safe_sum("Head Office")
    gey = safe_sum("Engineering Yard")

    # Total Gravitas Revenue
    maintenance = filtered_cost[filtered_cost['Type of Activity'].str.contains('maintenance', case=False, na=False)]
    total_gravitas = gho + gey + gravitas_partner
    gravitas_revenue = f"₦{total_gravitas:,.0f}"

    # Fuel Costs
    fuel_rows = filtered_cost[filtered_cost['Type of Activity'].str.contains('Fuel', case=False, na=False)]
    fuel_cost = fuel_rows['Amount (NGN)'].sum()

    df_table.columns = df_table.columns.astype(str).str.strip().str.replace('\u00A0', '', regex=True)

    # Build cost breakdown data
    cost_data = pd.DataFrame({
        'Category': ['Fuel', 'Routine Maintenance', 'Corrective Maintenance'],
        'Cost': [fuel_cost, routine_cost, corrective_cost],
        'Type': ['Fuel', 'Routine', 'Corrective']
    })
    columns_to_sum = ['Cedar A', 'DIC', 'NBIC 1', 'NBIC 2', 'HELIUM', 
                    'Rosewood A', 'Rosewood B', 'Tuck-shop', 'Cedar B']

    # Sort by cost descending
    cost_data = cost_data.sort_values('Cost', ascending=False)
    existing_cols = [c for c in columns_to_sum if c in df_table.columns]

    # Create horizontal bar chart
    fig_cost_bar = px.bar(
        cost_data,
        x='Cost',
        y='Category',
        color='Type',
        orientation='h',
        text='Cost',
        color_discrete_map={
            'Fuel': '#2C3E50',
            'Routine': '#4A90E2',
            'Corrective': '#E67E22'
        },
        labels={'Cost': 'Amount (₦)'})
    
    fig_cost_bar.update_layout(
    bargap=0.15,        # space between bars (0 = no space)
    bargroupgap=0.05    # space between grouped bars
    )

    
    subs_sum = (
        df_table[existing_cols]
            .replace('-', 0)
            .apply(pd.to_numeric, errors='coerce')
            .fillna(0)
            .to_numpy()
            .sum()
    )

    fig_cost_bar.update_traces(
        texttemplate='₦%{text:,.0f}',
        textposition='inside',
        textfont=dict(color='white', size=14, family='Arial Black')
    )
    total_subs = subs_sum + gravitas_subscriber
    gravitas_subs_revenue = f"₦{total_subs:,.0f}"    

    fig_cost_bar.update_layout(
        title=dict(text='Cost Breakdown (Fuel + Maintenance)', font=dict(size=14, color='#C7A64F'), x=0.5, pad=dict(t=10, b=20)),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, categoryorder='total ascending'),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=40, l=130, r=120),
        height=400,)

    filtered_cost = local_df_cost_2025.copy() 
    
    if selected_generators:
        filtered_cost = filtered_cost[filtered_cost["Generator"].isin(selected_generators)]
    
    if selected_months:
        filtered_cost = filtered_cost[filtered_cost["Month"].isin(selected_months)]
    
    fig_pie = px.pie(
        filtered_cost,
        names='Type of Activity',
        values='Amount (NGN)',
        color_discrete_sequence=brand_colors,
    )   

    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(
        title=dict(text='💸 Cost Breakdown (2025)', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=40, l=130, r=120),
    )

    # Apply a logarithmic scale to the x-axis to prevent large values from overshadowing smaller ones
    fig_cost_bar.update_xaxes(type="log")

    # --- Total Cost KPI ---
    total_cost_all = filtered_cost['Amount (NGN)'].sum()
    total_cost_display = f"₦{total_cost_all:,.0f}"

    # Add total cost annotation
    fig_cost_bar.add_annotation(
        x=total_cost_all * 1.02,
        y=0,
        text=f"Total Cost: ₦{total_cost_all:,.0f}",
        showarrow=False,
        font=dict(size=15, color="#C7A64F", family="Arial Black"),
        xanchor="left"
    )

    # --- Fuel Chart ---
    filtered_fuel = local_df_supplied.copy()
    if selected_months:
        filtered_fuel = filtered_fuel[filtered_fuel['Month'].isin(selected_months)]
    
    # Convert to numeric safely
    for col in ['Fuel Purchased', 'Total Fuel Used']:
        filtered_fuel[col] = pd.to_numeric(filtered_fuel[col], errors='coerce')
    
    filtered_fuel = filtered_fuel.dropna(subset=['Fuel Purchased','Total Fuel Used'])

    if not filtered_fuel.empty:
        fig_fuel = px.bar(
            filtered_fuel,
            x='Month',
            y=['Fuel Purchased', 'Total Fuel Used'],
            barmode='group',
            labels={'value': 'Litres', 'variable': 'Fuel Metric'},
            color_discrete_sequence=brand_colors[:3]
        )
        
        # Add values inside bars
        fig_fuel.update_traces(
            texttemplate='%{y:.0f}', 
            textposition='inside',
            textfont=dict(color='white', size=11)
        )
    else:
        fig_fuel = px.bar(title="No fuel data available")

    fig_fuel.update_layout(
        title=dict(text='Fuel Management', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=28, b=8, l=20, r=120),
        legend=dict(
            orientation='v',
            x=1.02,
            xanchor='left',
            y=1,
            yanchor='top',
            font=dict(size=10),
            bgcolor='rgba(0,0,0,0)',
            borderwidth=0
        )
    )

    # --- Downtime Chart ---
    filtered_downtime = local_df_downTime.copy()

    if selected_months:
        filtered_downtime = filtered_downtime[filtered_downtime['Month'].isin(selected_months)]

    if selected_generators:
        filtered_downtime = filtered_downtime[filtered_downtime['Generator'].isin(selected_generators)]

    unplanned_outage_hours = filtered_downtime['Duration_Hours'].sum()
    unplanned_outage_display = f"{unplanned_outage_hours:,.1f}h"
    
    fig_down = px.bar(
        filtered_downtime,
        x="Month",
        y="Duration_Hours",
        color="Generator",
        text_auto=True,
        barmode="group",
        color_discrete_sequence=brand_colors,
    )

    # Use logarithmic scale to better visualize varying downtime durations
    fig_down.update_yaxes(type="log")

    fig_down.update_layout(
        title=dict(text='🛠️ Generator Downtime', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
        xaxis_title="Month",
        template="plotly_white",
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=28, b=40, l=40, r=160),
        legend=dict(
            orientation='v',
            x=1.03,
            xanchor='left',
            y=1,
            yanchor='top',
            font=dict(size=10),
            bgcolor='rgba(0,0,0,0)',
            borderwidth=0
        )
    )




    # --- Stock Chart ---
    filtered_stock = local_df_rc_melt.copy()

    if selected_months:
        filtered_stock = filtered_stock[filtered_stock['Month'].isin(selected_months)]

    if selected_generators:
        filtered_stock = filtered_stock[filtered_stock['Generator_Size'].isin(selected_generators)]

    if selected_filter:
        filtered_stock = filtered_stock[filtered_stock['Filter_Type'].isin(selected_filter)]

    if not filtered_stock.empty:
        # Aggregate stock data by month, generator size, and filter type
        stock_detailed = filtered_stock.groupby(['Month','Generator_Size', 'Filter_Type'])[['Consumed_Stock', 'Remaining_Stock']].sum().reset_index()
        
        if stock_detailed['Month'].dtype == 'object' and '-' in str(stock_detailed['Month'].iloc[0]):
            stock_detailed['Month'] = pd.to_datetime(stock_detailed['Month']).dt.strftime('%B')
        
        # Sum to get monthly totals
        stock_monthly = stock_detailed.groupby('Month', as_index=False)[['Consumed_Stock', 'Remaining_Stock']].sum()
        
        # Sort months chronologically
        month_order = ["January","February","March","April","May","June","July","August","September","October","November","December"]
        stock_monthly['Month'] = pd.Categorical(stock_monthly['Month'], categories=month_order, ordered=True)
        stock_monthly = stock_monthly.sort_values('Month')
        
        # Create bar chart with consumed vs remaining stock
        fig_stock = px.bar(
            stock_monthly,
            x='Month',
            y=['Consumed_Stock', 'Remaining_Stock'],
            barmode='group',
            labels={'Month': 'Month', 'value': 'Units'},
            color_discrete_sequence=['#C7A64F', '#2C3E50']
        )
    else:
        fig_stock = px.bar(title="No stock data available")

    fig_stock.update_layout(
        title=dict(text='📦 Stock Inventory', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=28, b=8, l=20, r=120),
        legend=dict(
            orientation='v',
            x=1.02,
            xanchor='left',
            y=1,
            yanchor='top',
            font=dict(size=10),
            bgcolor='rgba(0,0,0,0)',
            borderwidth=0
        )
    )

    


    fig_stock.update_xaxes(tickangle=-45)

    # --- Runtime Chart ---
    filtered_runtime = local_df_agg.copy()

    if selected_months:
        filtered_runtime = filtered_runtime[filtered_runtime['Month'].isin(selected_months)]

    if selected_generators:
        filtered_runtime = filtered_runtime[filtered_runtime['Generator'].isin(selected_generators)]

    if not filtered_runtime.empty:
        # Sum hours operated by generator
        gen_hours = filtered_runtime.groupby('Generator')['Hours Operated'].sum().reset_index()
        
        total_hours_all_gens = gen_hours['Hours Operated'].sum()
        if total_hours_all_gens > 0:
            gen_hours['Percentage'] = (gen_hours['Hours Operated'] / total_hours_all_gens) * 100
        else:
            gen_hours['Percentage'] = 0

        # Sort from most-used to least-used
        gen_hours = gen_hours.sort_values('Hours Operated', ascending=False)

        fig_runtime = px.bar(
            gen_hours,
            x='Generator',
            y='Hours Operated',
            text='Percentage',
            custom_data=['Percentage'],
            labels={'Hours Operated': 'Total Hours Operated', 'Generator': 'Generator'},
            color='Generator',
            color_discrete_sequence=brand_colors
        )
        # Format text as percentage and customize hover info
        fig_runtime.update_traces(
            texttemplate='%{text:.1f}%', 
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Hours: %{y:,.0f}h<br>Usage: %{customdata[0]:.1f}%<extra></extra>'
        )
        fig_runtime.update_layout(showlegend=False)
        
        # Add padding to y-axis to prevent text from being cut off
        fig_runtime.update_yaxes(range=[0, gen_hours['Hours Operated'].max() * 1.15])
    else:
        # Create empty bar chart if no data
        fig_runtime = go.Figure()
        fig_runtime.add_annotation(text="No runtime data available", showarrow=False)

    fig_runtime.update_layout(
        title=dict(text='⏱️ Generator Usage (% of Total Runtime)', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
        xaxis_title=None,
        yaxis_title="Hours Operated",
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, b=40, l=40, r=40)
    )

    # --- Percent Change KPIs ---
    revenue_change_display = "N/A"
    fuel_change_display = "N/A"

    # Calculate current fuel usage
    filtered_fuel_kpi = local_df_supplied.copy()
    if selected_months:
        filtered_fuel_kpi = filtered_fuel_kpi[filtered_fuel_kpi['Month'].isin(selected_months)]
    total_fuel_used = pd.to_numeric(filtered_fuel_kpi['Total Fuel Used'], errors='coerce').sum()
    
    if selected_months:
        # Current Revenue
        current_total_revenue = total_revenue_value

        # Determine the previous period
        month_order = list(calendar.month_name)[1:]
        selected_indices = sorted([month_order.index(m) for m in selected_months])
        min_index = selected_indices[0]
        num_months = len(selected_months)
        
        # Ensure the selected months are a continuous block (e.g., Feb-Mar, not Feb-Apr)
        is_contiguous = all(selected_indices[i] == selected_indices[0] + i for i in range(num_months))
        prev_start_index = min_index - num_months

        if prev_start_index >= 0 and is_contiguous:
            # Previous period exists and the selection is contiguous
            prev_indices = range(prev_start_index, min_index)
            previous_months = [month_order[i] for i in prev_indices]

            # Previous Revenue
            prev_power_df = local_power_df[local_power_df['Month'].isin(previous_months)].copy()
            prev_power_df['Resident Address'] = prev_power_df['Meter Number'].map(meter_to_name).fillna(prev_power_df['Resident Address'])
            
            prev_meter_df = local_df_meter[local_df_meter["Month"].isin(previous_months)].copy()
            prev_meter_df['Total Revenue'] = pd.to_numeric(prev_meter_df['Total Revenue'], errors='coerce').fillna(0)

            if selected_locations:
                prev_power_df = prev_power_df[prev_power_df['Resident Address'].isin(selected_locations)]
                prev_meter_df = prev_meter_df[prev_meter_df['Location'].isin(selected_locations)]

            previous_total_revenue = prev_power_df['Amount'].sum() + prev_meter_df['Total Revenue'].sum()

            # Revenue % Change
            if previous_total_revenue > 0:
                percent_change = ((current_total_revenue - previous_total_revenue) / previous_total_revenue) * 100
                arrow, color = ("▲", "green") if percent_change > 0 else (("▼", "red") if percent_change < 0 else ("", "grey"))
                revenue_change_display = html.Span([f"{percent_change:,.2f}% ", html.Span(arrow, style={'color': color, 'fontSize': '1.2em'})])

            # Fuel % Change
            prev_fuel_df = local_df_supplied[local_df_supplied['Month'].isin(previous_months)]
            previous_total_fuel_used = pd.to_numeric(prev_fuel_df['Total Fuel Used'], errors='coerce').sum()

            if previous_total_fuel_used > 0:
                percent_change = ((total_fuel_used - previous_total_fuel_used) / previous_total_fuel_used) * 100
                # For fuel, an increase is bad (red), a decrease is good (green)
                arrow, color = ("▲", "red") if percent_change > 0 else ("▼", "green")
                fuel_change_display = html.Span([f"💧 {percent_change:,.2f}% ", html.Span(arrow, style={'color': color, 'fontSize': '1.2em'})])


    # === Operated Hours & Outage Calculation ===
    filtered_runtime = local_df_agg.copy()
    if selected_months:
        filtered_runtime = filtered_runtime[filtered_runtime['Month'].isin(selected_months)]
    if selected_generators:
        filtered_runtime = filtered_runtime[filtered_runtime['Generator'].isin(selected_generators)]

    actual_operated_hours = filtered_runtime['Hours Operated'].sum()

    # Define daily generator schedule based on day of week
    # Weekday mapping: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
    daily_schedule = {
        0: {  # Monday
            "80kva": 11,      # 7AM - 6PM
            "55kva": 12,      # 7PM Monday - 7AM Tuesday
        },
        1: {  # Tuesday
            "80kva": 11,      # 7AM - 6PM
            "55kva": 12,      # 7PM Tuesday - 7AM Wednesday
        },
        2: {  # Wednesday
            "80kva": 11,      # 7AM - 6PM
            "55kva": 12,      # 7PM Wednesday - 7AM Thursday
        },
        3: {  # Thursday
            "80kva": 11,      # 7AM - 6PM
            "55kva": 12,      # 7PM Thursday - 7AM Friday
        },
        4: {  # Friday
            "80kva": 11,      # 7AM - 6PM
            "55kva": 19.5,    # 7PM Friday - 2:30PM Saturday
        },
        5: {  # Saturday
            "55kva": 12,      # 7PM Saturday - 7AM Sunday
        },
        6: {  # Sunday
            "200kva": 7,      # 7AM - 2PM
            "55kva": 12,      # 7PM Sunday - 7AM Monday
        }
    }

    # Determine date range
    current_year = int(selected_years[0]) if selected_years else 2025

    if selected_months:
        months = selected_months if isinstance(selected_months, list) else [selected_months]
        # Convert month names to numbers
        month_nums = [list(calendar.month_name).index(m) for m in months]
        start_month = min(month_nums)
        end_month = max(month_nums)
        
        start_date = datetime(current_year, start_month, 1)
        last_day = calendar.monthrange(current_year, end_month)[1]
        end_date = datetime(current_year, end_month, last_day)
    else:
        # If no month selected, use entire year
        start_date = datetime(current_year, 1, 1)
        end_date = datetime(current_year, 12, 31)

    # Calculate scheduled hours for the period
    date_range = pd.date_range(start_date, end_date, freq='D')
    weekday_counts = Counter(date_range.weekday)

    total_scheduled_hours = 0.0
    scheduled_breakdown = {}

    for weekday, count in weekday_counts.items():
        day_schedule = daily_schedule.get(weekday, {})
        
        for gen, hours_per_day in day_schedule.items():
            # Skip if generator not in selection
            if selected_generators and gen not in selected_generators:
                continue
            
            scheduled_hours = count * hours_per_day
            total_scheduled_hours += scheduled_hours
            
            day_name = calendar.day_name[weekday]
            key = f"{gen}_{day_name}"
            scheduled_breakdown[key] = scheduled_hours

    total_days = (end_date - start_date).days + 1
    total_hours_in_period = total_days * 24

    operated_hours_display = f"{actual_operated_hours:,.1f}h"

    # --- Final Fuel Change Check ---
    fuel_change_display = ""
    if selected_months and 'prev_start_index' in locals() and prev_start_index >= 0 and is_contiguous:
        previous_total_fuel_used = pd.to_numeric(prev_fuel_df['Total Fuel Used'], errors='coerce').sum()

        if previous_total_fuel_used > 0:
            percent_change = ((total_fuel_used - previous_total_fuel_used) / previous_total_fuel_used) * 100
            # For fuel, an increase is bad (red), a decrease is good (green)
            arrow, color = ("▲", "red") if percent_change > 0 else ("▼", "green")
            fuel_change_display = html.Span([f"💧 {percent_change:,.2f}% ", html.Span(arrow, style={'color': color, 'fontSize': '1.2em'})])

    return (
        fig_margin,
        fig_trans,
        totalRevenue,
        operated_hours_display,
        unplanned_outage_display,
        total_cost_display,
        revenue_change_display,
        fig_cost_bar,
        fig_fuel,
        fuel_change_display,
        fig_down,
        fig_stock,
        fig_runtime,
    )

if __name__ == "__main__":
    # Check if running as standalone executable
    if getattr(sys, 'frozen', False):
        # Open browser automatically in a separate thread
        threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:8050")).start()
        app.run(debug=False, port=8050)
    else:
        port = int(os.environ.get("PORT", 8050))
        # app.run(debug=True, host='0.0.0.0', port=port)
        app.run(debug=True, port=port)
