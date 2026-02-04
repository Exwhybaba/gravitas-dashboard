import pandas as pd
import threading
from datetime import datetime
import warnings
import constants

warnings.filterwarnings('ignore')

# --- Global Variables ---
data_lock = threading.Lock()
last_refresh_time = None
REFRESH_INTERVAL = 300  # 5 minutes in seconds

# Dataframes
df_meter = None
df_cost = None
df_cost_2025 = None
df_downTime = None
run_time = None
df_agg = None
df_supplied = None
df_stock = None
df_rc = None
df_rc_melt = None
power_df = None
df_electrical = None

def load_all_data():
    """Load and process data from Google Sheets with thread safety."""
    global df_meter, df_cost, df_cost_2025, df_downTime, run_time, df_agg
    global df_supplied, df_stock, df_rc, df_rc_melt, power_df, last_refresh_time, df_electrical
   
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
                df_meter.columns = df_meter.columns.str.strip()
                if 'Total Revenue' in df_meter.columns:
                    df_meter['Total Revenue'] = df_meter['Total Revenue'].astype(str).str.replace(',', '', regex=False)
                    df_meter['Total Revenue'] = df_meter['Total Revenue'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                    df_meter['Total Revenue'] = pd.to_numeric(df_meter['Total Revenue'], errors='coerce').fillna(0)

                if 'Year' in df_meter.columns:
                    df_meter['Year'] = df_meter['Year'].astype(str).str.replace(r'\.0', '', regex=True)
                elif 'Date' in df_meter.columns:
                    df_meter['Date'] = pd.to_datetime(df_meter['Date'])
                    df_meter['Year'] = df_meter['Date'].dt.strftime('%Y')

                if 'Month' in df_meter.columns:
                    df_meter['Month'] = df_meter['Month'].astype(str).str.strip()
                df_meter['Month'] = pd.Categorical(df_meter['Month'], categories=constants.MONTH_ORDER, ordered=True)

                # --- Cost Breakdown ---
                df_cost = df.parse(1)
                df_cost.columns = df_cost.columns.str.strip()
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
                    categories=constants.MONTH_ORDER,
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
                df_agg['Month'] = pd.Categorical(df_agg['Month'], categories=constants.MONTH_ORDER, ordered=True)
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
                        # Ensure Month is standardized to Month Name (e.g. "January")
                        try:
                            temp_dates = pd.to_datetime(df_stock['Month'], errors='coerce')
                            mask = temp_dates.notna()
                            df_stock.loc[mask, 'Month'] = temp_dates[mask].dt.strftime('%B')
                        except Exception:
                            pass
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
                power_df.columns = power_df.columns.str.strip()
                if 'Amount' in power_df.columns:
                    power_df['Amount'] = power_df['Amount'].astype(str).str.replace(',', '', regex=False)
                    power_df['Amount'] = power_df['Amount'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                    power_df['Amount'] = pd.to_numeric(power_df['Amount'], errors='coerce').fillna(0)

                # Prioritize existing Year/Month columns from source
                if 'Year' in power_df.columns:
                    power_df['Year'] = power_df['Year'].astype(str).str.replace(r'\.0', '', regex=True).str.strip()
                
                if 'Month' in power_df.columns:
                    power_df['Month'] = power_df['Month'].astype(str).str.strip()

                if 'Transaction Date' in power_df.columns:
                    # Robust date parsing (still useful for filling gaps)
                    if not pd.api.types.is_datetime64_any_dtype(power_df['Transaction Date']):
                        # Try parsing with dayfirst=True (common in Nigeria)
                        temp_dates = pd.to_datetime(power_df['Transaction Date'].astype(str), dayfirst=True, errors='coerce')
                        # If too many failures (>80%), try standard parsing (Month-First)
                        if temp_dates.isna().mean() > 0.8:
                            temp_dates = pd.to_datetime(power_df['Transaction Date'].astype(str), errors='coerce')
                        power_df['Transaction Date'] = temp_dates

                    # Fill missing Year/Month from Transaction Date if needed
                    if 'Year' not in power_df.columns:
                        power_df['Year'] = power_df['Transaction Date'].dt.strftime('%Y')
                    else:
                        power_df['Year'] = power_df['Year'].fillna(power_df['Transaction Date'].dt.strftime('%Y'))

                    if 'Month' not in power_df.columns:
                        power_df['Month'] = power_df['Transaction Date'].dt.strftime('%B')
                    else:
                        power_df['Month'] = power_df['Month'].fillna(power_df['Transaction Date'].dt.strftime('%B'))

                # Only drop rows if we absolutely lack a Month (grouping key)
                power_df = power_df.dropna(subset=['Month'])

                power_df.reset_index(drop=True, inplace=True)

                # --- Electrical Inventory (Last Sheet) ---
                df_electrical = df.parse(7)
               
                last_refresh_time = current_time
                print("Data refresh completed successfully")
               
        except Exception as e:
            print(f"Error refreshing data: {e}")
