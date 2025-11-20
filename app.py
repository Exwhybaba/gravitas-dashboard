from dash import dash_table, dash, html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import seaborn as sb
import pandas as pd
from dash import Dash, dcc, html, Input, Output, callback_context
import os
import warnings
import logging
from functools import lru_cache
from datetime import datetime
import copy

warnings.filterwarnings('ignore')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
URL = "https://docs.google.com/spreadsheets/d/1O-mPctFgp6oqd-VK9YKHyPq-asuve2ZM/export?format=xlsx"
MONTH_ORDER = ["January","February","March","April","May","June","July","August","September","October","November","December"]

@lru_cache(maxsize=1)
def load_initial_data():
    """Load and process all data once at startup. Cached for performance."""
    logger.info("Loading initial data from source...")
    
    try:
        df = pd.ExcelFile(URL)
        
        # Meter data
        df_meter = df.parse(0)
        df_meter['Month'] = pd.Categorical(df_meter['Month'], categories=MONTH_ORDER, ordered=True)
        
        # Cost data
        df_cost = df.parse(1)
        
        # Safe data modifications with validation
        def safe_set_value(dataframe, index, column, value):
            """Safely set a value in dataframe with bounds checking"""
            if index < len(dataframe):
                dataframe.at[index, column] = value
            else:
                logger.warning(f"Index {index} out of bounds for {column}")
        
        safe_set_value(df_cost, 125, 'Rate', 127000)
        safe_set_value(df_cost, 125, 'Amount (NGN)', 127000)
        safe_set_value(df_cost, 126, 'Rate', 127000)
        safe_set_value(df_cost, 126, 'Amount (NGN)', 127000)
        
        df_cost['Generator'].replace(['new 80kva', 'both 80kva', 'old 80kva', 'new 200kva', '55Kva'],
                                     ['80kva', '80kva', '80kva', '200kva', '55kva'], inplace=True)
        
        df_cost['Date'] = pd.to_datetime(df_cost['Date'], errors='coerce')
        df_cost['Year'] = df_cost['Date'].dt.strftime('%Y')
        df_cost['Month'] = df_cost['Date'].dt.strftime('%B')
        
        corr_Rout = df_cost.loc[df_cost['Type of Activity'].isin(['Corrective maintenance', 'Routine Maintenance', 'Fuel'])].copy()
        if 'id' in corr_Rout.columns:
            corr_Rout.drop(columns=['id'], inplace=True)
        corr_Rout.reset_index(drop=True, inplace=True)
        
        df_cost_2025 = corr_Rout.loc[corr_Rout['Year'] == '2025'].copy()
        
        # Downtime data
        df_downTime = df.parse(2)
        df_downTime = df_downTime.sort_values(by='Duration_Hours', ascending=False)
        df_downTime['Generator'] = df_downTime['Generator'].replace('88kva', '80kva')
        
        # Group downtime by month and generator
        df_downTime["Month"] = pd.Categorical(
            df_downTime["Month"],
            categories=MONTH_ORDER,
            ordered=True
        )
        df_downTime = df_downTime.groupby(["Month", "Generator"], as_index=False)["Duration_Hours"].sum()
        
        # Runtime data
        run_time = df.parse(4)
        run_time['Date'] = pd.to_datetime(run_time['Date'], errors='coerce')
        run_time['Month'] = run_time['Date'].dt.strftime('%B')
        run_time['Day'] = run_time['Date'].dt.strftime('%A')
        df_agg = run_time.groupby(['Month', 'Generator'], as_index=False)['Hours Operated'].sum()
        df_agg['Month'] = pd.Categorical(df_agg['Month'], categories=MONTH_ORDER, ordered=True)
        df_agg = df_agg.sort_values(by='Month')
        
        # Fuel supplied data
        df_supplied = df.parse(3)
        safe_set_value(df_supplied, 1, 'Total Fuel Used', 4200)
        safe_set_value(df_supplied, 1, 'Fuel Added (Total)', 3000)
        
        if len(df_supplied) > 10:
            df_supplied.drop(index=10, inplace=True)
            
        df_supplied['Date'] = pd.to_datetime(df_supplied['Date'], errors='coerce')
        df_supplied['Month'] = df_supplied['Date'].dt.strftime('%B')
        
        # Stock data
        df_stock = df.parse(5)
        df_stock['Total Available Stock'] = df_stock['Opening_Stock'] + df_stock['Purchased_Stock']
        df_stock.rename(columns={"Month": "Date"}, inplace=True)
        df_stock['Month'] = pd.to_datetime(df_stock['Date'], errors='coerce').dt.strftime('%B')
        
        # Aggregate by Generator_Size + Filter_Type
        df_rc = df_stock.groupby(['Generator_Size','Filter_Type'], as_index=False).agg({
            'Consumed_Stock':'sum',
            'Remaining_Stock':'sum'
        })
        
        # Melt for stacked plotting
        df_rc_melt = df_rc.melt(
            id_vars=['Generator_Size','Filter_Type'],
            value_vars=['Consumed_Stock','Remaining_Stock'],
            var_name='Stock_Status',
            value_name='Units'
        )
        
        # Power transactions data
        power_df = df.parse(6)
        
        # Convert Transaction Date safely
        power_df['Transaction Date'] = power_df['Transaction Date'].astype(str)
        power_df['Transaction Date'] = pd.to_datetime(power_df['Transaction Date'], errors='coerce')
        power_df = power_df.dropna(subset=['Transaction Date'])
        
        if 'Transaction Date' in power_df.columns:
            power_df['Month'] = power_df['Transaction Date'].dt.strftime('%B')
        
        power_df.reset_index(drop=True, inplace=True)
        
        logger.info("Data loaded successfully")
        
        return {
            'df_meter': df_meter,
            'df_cost': df_cost,
            'df_cost_2025': df_cost_2025,
            'df_downTime': df_downTime,
            'run_time': run_time,
            'df_agg': df_agg,
            'df_supplied': df_supplied,
            'df_stock': df_stock,
            'df_rc_melt': df_rc_melt,
            'power_df': power_df
        }
        
    except Exception as e:
        logger.error(f"Error loading initial data: {e}")
        # Return empty dataframes to prevent app crash
        return {
            'df_meter': pd.DataFrame(),
            'df_cost': pd.DataFrame(),
            'df_cost_2025': pd.DataFrame(),
            'df_downTime': pd.DataFrame(),
            'run_time': pd.DataFrame(),
            'df_agg': pd.DataFrame(),
            'df_supplied': pd.DataFrame(),
            'df_stock': pd.DataFrame(),
            'df_rc_melt': pd.DataFrame(),
            'power_df': pd.DataFrame()
        }

# Load data once at startup
DATA = load_initial_data()

def get_data_copy():
    """Return deep copies of all dataframes to ensure thread safety"""
    return {key: copy.deepcopy(value) for key, value in DATA.items()}

# Define all location/address options for filtering
all_locations = sorted(list(set(
    list(DATA['df_meter']["Location"].unique()) +
    ['Rosewood', 'Cedar A', 'Tuck-shop', 'Cedar B',
     'Gravitas Head Office', 'Engineering Yard', 'NBIC 2', 'NBIC 1',
     'HELIUM ', 'DIC']
))) if not DATA['df_meter'].empty else []

# Location filter (now includes both meter locations and transaction addresses)
metr_loc = dcc.Dropdown(
    id='location_filter',
    options=[{"label": loc, "value": loc} for loc in all_locations],
    placeholder="Select Location",
    multi=True,
    style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
)

# Month filter - safely get unique months
available_months = DATA['df_meter']["Month"].unique() if not DATA['df_meter'].empty else []
mtr_month = dcc.Dropdown(
    id='month_filter',
    options=[{"label": m, "value": m} for m in available_months],
    placeholder="Select Month",
    multi=True,
    style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
)

# Generator dropdown - safely get unique generators
available_generators = sorted(DATA['df_cost_2025']["Generator"].unique()) if not DATA['df_cost_2025'].empty else []
gen_dropdown = dcc.Dropdown(
    id='generator_type',
    options=[{"label": gen, "value": gen} for gen in available_generators],
    placeholder="Select Generator Type",
    multi=True,
    style={'width': '90%', 'marginTop': '30%', "marginLeft": "5%"}
)

# Graph components
consChart = dcc.Graph(id='consumption_chart', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"}, className='consumption-chart')

consumpLine = dcc.Graph(id='consumption_line', config={"responsive": True},
    style={"width": "100%", "height": "100%", "flex": "1 1 auto"}, className='consumption-line')

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


# Transactions table markup
transTable = dash_table.DataTable(
    id='transactions_table',
    columns=[{"name": "Meter Number", "id": "Meter Number"}],
    data=[],
    page_size=8,
    fixed_rows={'headers': True},
    style_table={'overflowX': 'auto', 'height': '90%', 'width': '98%'},
    style_header={
        'backgroundColor': '#f7f9fc',
        'fontWeight': '20',
        'borderBottom': '1px solid #ddd',
        'fontSize': '12px'
    },
    style_cell={
        'textAlign': 'left',
        'padding': '4px',
        'whiteSpace': 'normal',
        'height': 'auto',
        'minWidth': '25px',
        'maxWidth': '150px',
        'overflow': 'hidden',
        'textOverflow': 'ellipsis'
    },
    css=[
        {
            'selector': '.dash-table-container .dash-spreadsheet-container',
            'rule': 'height: calc(100% - 36px) !important;'
        }
    ]
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.config.suppress_callback_exceptions = True
app.layout = html.Div([
    html.Meta(name='viewport', content='width=device-width, initial-scale=1.0'),
    html.Div([
        html.Img(
            src=app.get_asset_url('images/Gracefield_logo.png'),
            className="logo",
            alt="Gracefield logo"
        ),
        mtr_month,
        metr_loc, 
        gen_dropdown,
        html.Button("Power Analytics", id="tab1-btn", className="tab-btn active-tab", 
                   style={"marginLeft": "0.5rem", "marginTop": "4rem"}),
        html.Button("Operations", id="tab2-btn", className="tab-btn",
                   style={"marginLeft": "0.8rem", "marginTop": "4rem"})
    ], className="sidebar"),
    
    html.Div([
        html.H2("Power Dashboard", className="title"),
        html.Div([
            html.Div("💼", className="kpi-icon"),
            html.Div([
                html.P("Gravitas Revenue", className="kpi-label"),
                html.H3(id="gravitas_revenue", className="kpi-value")
            ], className="kpi-text")
        ], className="kpi-card"),

        html.Div([
            html.Div("👥", className="kpi-icon"),
            html.Div([
                html.P("Subscriber Revenue", className="kpi-label"),
                html.H3(id="subs_revenue", className="kpi-value")
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
                html.P("Planned Outage", className="kpi-label"),
                html.H3(id="planned_outage", className="kpi-value")
            ], className="kpi-text")
        ], className="kpi-card")
    ], className="header"),

    html.Div([
        html.Div([
            consumpLine
        ], className="card-1"),

        html.Div([
            consChart
        ], className="card-2"),

        html.Div([
            transTable
        ], className="card-3"),

        html.Div([
            costPie
        ], className="card-4"),    
    ], id="tab-1", className="section"),

    html.Div([
        html.Div([
            fuelChart
        ], className="card-1"),

        html.Div([
            downtimeChart
        ], className="card-2"),

        html.Div([
            stockChart
        ], className="card-3"),

        html.Div([
            runtimeChart
        ], className="card-4"),    
    ], id="tab-2", className="section", style={"display": "none"}),
], className="app-grid")

# Tab switching callback
@app.callback(
    [
        Output('tab-1', 'style'),
        Output('tab-2', 'style'),
        Output('tab1-btn', 'className'),
        Output('tab2-btn', 'className'),
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
        return {'display': 'flex'}, {'display': 'none'}, 'tab-btn active-tab', 'tab-btn'
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'tab1-btn':
        return {'display': 'flex'}, {'display': 'none'}, 'tab-btn active-tab', 'tab-btn'
    else:
        return {'display': 'none'}, {'display': 'flex'}, 'tab-btn', 'tab-btn active-tab'

@app.callback(
    [
        Output('consumption_chart', 'figure'),
        Output('consumption_line', 'figure'),
        Output('transactions_table', 'data'),
        Output('transactions_table', 'columns'),
        Output('gravitas_revenue', 'children'),
        Output('subs_revenue', 'children'),
        Output('operated_hours', 'children'),
        Output('planned_outage', 'children'),
        Output('cost_pie', 'figure'),
        Output('fuel_chart', 'figure'),
        Output('downtime_chart', 'figure'),
        Output('stock_chart', 'figure'),
        Output('runtime_chart', 'figure'),
    ],
    [
        Input('location_filter', 'value'),
        Input('month_filter', 'value'),
        Input('generator_type', 'value'),
    ]
)
def update_chart(selected_locations, selected_months, selected_generators):
    """Update all charts and data based on user filters - thread-safe version"""
    
    # Get thread-safe copies of data
    data = get_data_copy()
    
    # Handle empty data case
    if data['df_meter'].empty:
        empty_fig = px.bar(title="No data available")
        empty_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return [empty_fig] * 13
    
    filtered_meter = data['df_meter'].copy()

    filtered_meter['Location'] = filtered_meter['Location'].str.strip()
    selected_locations = [loc.strip() for loc in selected_locations] if selected_locations else []


    if selected_locations:
        filtered_meter = filtered_meter[filtered_meter["Location"].isin(selected_locations)]

    if selected_months:
        filtered_months = selected_months if isinstance(selected_months, list) else [selected_months]
        filtered_meter = filtered_meter[filtered_meter["Month"].isin(filtered_months)]

    filtered_meter['Rate'] = filtered_meter['Location'].apply(lambda x: 285 if x in ['9mobile', 'Providus'] else 100)
    filtered_meter['Amount'] = filtered_meter['Rate'] * filtered_meter['Monthly_Consumption']
    
    gravitas_partner = filtered_meter.loc[
        filtered_meter['Location'].isin(['9mobile', 'Providus']), "Amount"
    ].sum()

    gravitas_subscriber = filtered_meter.loc[
        filtered_meter['Location'] == 'Canteen', "Amount"
    ].sum()
    
    # --- Bar chart with brand-aligned color palette ---
    brand_colors = ['#C7A64F', '#2C3E50', "#5E7286", '#F4E4C1', '#E8D5B7']
    
    fig_bar = px.bar(
        filtered_meter,
        x='Location',
        y='Monthly_Consumption',
        color='Location',
        text_auto=False,
        labels={'Monthly_Consumption': 'Consumption'},
        color_discrete_sequence=brand_colors
    )

    fig_bar.update_layout(
        title=dict(text='⚡ Power Consumption by Location', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
        showlegend=False,
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=28, b=8, l=20, r=20)
    )

    # --- Line chart with brand colors ---
    fig_line = px.line(
        filtered_meter,
        x='Month',
        y='Amount',
        color='Location',
        markers=True,
        color_discrete_sequence=brand_colors
    )

    fig_line.update_layout(
        title=dict(text='⚡ Monthly Consumption Amount Trend', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
        xaxis_title='Month',
        yaxis_title='Amount',
        template="plotly_white",
        showlegend=False,
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=28, b=8, l=20, r=20)
    )
    
    # Style the line traces with gold tones
    fig_line.update_traces(line=dict(width=2.5))

    # --- Transactions table ---
    table_df = data['power_df'].copy()

    # Filter by month
    if selected_months:
        months_selected = selected_months if isinstance(selected_months, list) else [selected_months]
        table_df = table_df[table_df['Month'].isin(months_selected)]

    # Fix addresses to match the corrected names
    if not table_df.empty:
        table_df.loc[table_df['Meter Number'] == 23220035788, "Resident Address"] = 'Rosewood'
        table_df.loc[table_df['Meter Number'] == 4293682789, "Resident Address"] = 'NBIC 2' 

        mask = (table_df['Resident Address'] == 'C A') & (table_df['Meter Number'] == 4293684496)
        if not table_df.loc[mask].empty:
            min_index = table_df.loc[mask, 'Amount'].idxmin()
            table_df.loc[min_index, 'Resident Address'] = 'Cedar B'

    # Filter by selected location/address
    table_df['Resident Address'] = table_df['Resident Address'].str.strip()
    selected_locations = [loc.strip() for loc in selected_locations] if selected_locations else []
    
    if selected_locations:
        locations_selected = selected_locations if isinstance(selected_locations, list) else [selected_locations]
        table_df = table_df[table_df['Resident Address'].isin(locations_selected)]

    if not table_df.empty:
        pivot = pd.pivot_table(
            table_df,
            values='Amount',
            index='Meter Number',
            columns='Resident Address',
            aggfunc='sum'
        ).fillna('-').reset_index()
    else:
        pivot = pd.DataFrame(columns=['Meter Number'])

    table_data = pivot.to_dict('records')
    table_columns = [{"name": str(col), "id": str(col)} for col in pivot.columns]

    df_table = pd.DataFrame(table_data)

    # --- Gravitas Partner Revenue ---
    def safe_sum(col):
        if col in df_table.columns:
            return pd.to_numeric(df_table[col].replace('-', 0), errors='coerce').sum()
        return 0

    gho = safe_sum("Gravitas Head Office")
    gey = safe_sum("Gravitas Engineering Yard")

    gravitas_revenue = gho + gey + gravitas_partner

    # --- Subscriber Revenue ---
    # Fix column names – remove trailing spaces and invisible unicode
    df_table.columns = df_table.columns.str.strip().str.replace('\u00A0', '', regex=True)

    # Normalize subscriber columns list
    columns_to_sum = ['C A', 'DIC', 'NBIC 1', 'NBIC 2', 'HELIUM', 
                     'Rosewood', 'Bites To Eat [Tuck-shop]', 'Cedar B']

    # Only sum columns that actually exist
    existing_cols = [c for c in columns_to_sum if c in df_table.columns]

    # Convert everything inside those columns to numeric safely
    subs_sum = (
        df_table[existing_cols]
            .replace('-', 0)
            .apply(pd.to_numeric, errors='coerce')
            .fillna(0)
            .to_numpy()
            .sum()
    )

    gravitas_subs_revenue = subs_sum + gravitas_subscriber

    # --- Cost Pie Chart ---
    filtered_cost = data['df_cost_2025'].copy() 
    
    # Filter by generator type
    if selected_generators:
        filtered_cost = filtered_cost[filtered_cost["Generator"].isin(selected_generators)]
    
    # Filter by month  
    if selected_months:
        filtered_cost = filtered_cost[filtered_cost["Month"].isin(selected_months)]
    
    if not filtered_cost.empty:
        fig_pie = px.pie(
            filtered_cost,
            names='Type of Activity',
            values='Amount (NGN)',
            color_discrete_sequence=brand_colors,
        )   
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    else:
        fig_pie = px.pie(title="No cost data available")
    
    fig_pie.update_layout(
        title=dict(text='💸 Cost Breakdown (2025)', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=28, b=8, l=8, r=8)
    )

    # --- Fuel Chart (Tab-2) ---
    filtered_fuel = data['df_supplied'].copy()
    if selected_months:
        filtered_fuel = filtered_fuel[filtered_fuel['Month'].isin(selected_months)]
    
    # Convert to numeric to avoid type issues
    filtered_fuel['Total Fuel Used'] = pd.to_numeric(filtered_fuel['Total Fuel Used'], errors='coerce')
    filtered_fuel['Fuel Added (Total)'] = pd.to_numeric(filtered_fuel['Fuel Added (Total)'], errors='coerce')
    filtered_fuel = filtered_fuel.dropna(subset=['Total Fuel Used', 'Fuel Added (Total)'])
    
    if not filtered_fuel.empty:
        fig_fuel = px.bar(
            filtered_fuel,
            x='Month',
            y=['Total Fuel Used', 'Fuel Added (Total)'],
            barmode='group',
            labels={'Month': 'Month', 'value': 'Fuel (Litres)'},
            color_discrete_sequence=['#C7A64F', '#2C3E50']
        )
    else:
        # Empty chart if no data
        fig_fuel = px.bar(title="No fuel data available")
    
    # Place legend to the right of the chart
    fig_fuel.update_layout(
        title=dict(text='⛽ Fuel Management', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
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

    # --- Downtime Chart (Tab-2) ---
    filtered_downtime = data['df_downTime'].copy()

    if selected_months:
        filtered_downtime = filtered_downtime[filtered_downtime['Month'].isin(selected_months)]
    
    if not filtered_downtime.empty:
        fig_down = px.bar(
            filtered_downtime,
            x="Month",
            y="Duration_Hours",
            color="Generator",
            text_auto=True,
            barmode="group",
            color_discrete_sequence=brand_colors,
        )
        # Set y-axis to log scale
        fig_down.update_yaxes(type="log")
    else:
        fig_down = px.bar(title="No downtime data available")

    # Format layout and move legend clear of the bars (right side)
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

    # --- Stock Chart (Tab-2) with brand colors ---
    if not data['df_rc_melt'].empty:
        fig_stock = px.bar(
            data['df_rc_melt'],
            x='Filter_Type',
            y='Units',
            color='Stock_Status',
            barmode='stack',
            labels={'Units': 'Units', 'Filter_Type': 'Filter Type'},
            color_discrete_sequence=['#C7A64F', '#34495E']
        )
    else:
        fig_stock = px.bar(title="No stock data available")
    
    # Move stock legend to the right
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

    # --- Runtime Chart (Tab-2) ---
    filtered_runtime = data['df_agg'].copy()

    if selected_months:
        filtered_runtime = filtered_runtime[filtered_runtime['Month'].isin(selected_months)]

    if selected_generators:
        filtered_runtime = filtered_runtime[filtered_runtime['Generator'].isin(selected_generators)]
    
    if not filtered_runtime.empty:
        fig_runtime = px.pie(
            filtered_runtime,
            names="Generator",
            values="Hours Operated",
            color_discrete_sequence=brand_colors,
            hole=0.4
        )
        fig_runtime.update_traces(textposition="inside", textinfo="percent+label")
    else:
        fig_runtime = px.pie(title="No runtime data available")

    # Apply same pie chart styling as Tab-1 cost_pie
    fig_runtime.update_layout(
        title=dict(text='⏱️ Generator Runtime', font=dict(size=12, color='#111827'), x=0.5, xanchor='center'),
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=28, b=8, l=8, r=8)
    )

    # Calculate Operated Hours and Planned Outage
    operated_hours = filtered_runtime['Hours Operated'].sum() if not filtered_runtime.empty else 0
    
    # Calculate total hours available in filtered months
    total_hours_available = 0
    if selected_months:
        filtered_months = selected_months if isinstance(selected_months, list) else [selected_months]
        # Days per month mapping
        days_in_month = {
            'January': 31, 'February': 28, 'March': 31, 'April': 30,
            'May': 31, 'June': 30, 'July': 31, 'August': 31,
            'September': 30, 'October': 31, 'November': 30, 'December': 31
        }
        for month in filtered_months:
            total_hours_available += days_in_month.get(month, 30) * 24
    else:
        # If no month filter, calculate for all months in data
        total_hours_available = len(data['df_agg']['Month'].unique()) * 30 * 24 if not data['df_agg'].empty else 0
    
    # Planned Outage = Total Available Hours - Operated Hours
    planned_outage = max(0, total_hours_available - operated_hours)

    # Format numeric values for display
    gravitas_revenue_str = f"₦{gravitas_revenue:,.0f}" if gravitas_revenue > 0 else "₦0"
    gravitas_subs_revenue_str = f"₦{gravitas_subs_revenue:,.0f}" if gravitas_subs_revenue > 0 else "₦0"
    operated_hours_str = f"{operated_hours:.0f}h" if operated_hours > 0 else "0h"
    planned_outage_str = f"{planned_outage:.0f}h" if planned_outage > 0 else "0h"

    return (fig_bar, fig_line, table_data, table_columns, 
            gravitas_revenue_str, gravitas_subs_revenue_str, 
            operated_hours_str, planned_outage_str,
            fig_pie, fig_fuel, fig_down, fig_stock, fig_runtime)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    debug_mode = os.environ.get("DASH_DEBUG_MODE", "false").lower() == "true"
    
    app.run(
        debug=debug_mode,
        host="0.0.0.0",
        port=port,
        dev_tools_ui=debug_mode,
        dev_tools_props_check=debug_mode
    )