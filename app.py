from dash import dash
import dash_bootstrap_components as dbc
import os
import threading
import sys
import webbrowser
import data_loader
import layout
import callbacks

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

# Initial data load
data_loader.load_all_data()

# --- App Layout ---
app.layout = layout.create_layout(app)
callbacks.register_callbacks(app)

if __name__ == "__main__":
    # Check if running as standalone executable
    if getattr(sys, 'frozen', False):
        # Open browser automatically in a separate thread
        threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:8050")).start()
        app.run(debug=False, port=8050)
    else:
        port = int(os.environ.get("PORT", 8050))
        # Bind to 0.0.0.0 for Render deployment
        app.run(debug=False, host='0.0.0.0', port=port)