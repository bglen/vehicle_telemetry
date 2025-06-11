from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash
import os, json
import pandas as pd

CAN_DIR = os.path.join(os.getcwd(), 'can_logs')
DBC_DIR = os.path.join(os.getcwd(), 'dbc')

app = Flask(__name__)
app.secret_key = 'replace-with-a-secure-random-key'

@app.route('/')
def index():
    return redirect(url_for('list_logs'))

# ——— CAN log routes ——————————————————————————————

# Log Page
@app.route('/logs')
def list_logs():
    entries = []
    for fn in sorted(os.listdir(CAN_DIR)):
        if not fn.endswith('.csv'):
            continue
        meta_path = os.path.join(CAN_DIR, fn.replace('.csv', '.json'))
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
        else:
            # fallback to filesystem time
            mtime = os.path.getmtime(os.path.join(CAN_DIR, fn))
            meta['timestamp'] = mtime
        entries.append(dict(
            filename=fn,
            metadata=meta
        ))
    return render_template('logs.html', entries=entries)

# Download Log
@app.route('/logs/download/<path:filename>')
def download_log(filename):
    return send_from_directory(CAN_DIR, filename, as_attachment=True)

# Rename Log
@app.route('/logs/rename/<path:filename>')
def rename_log(filename):
    return 0

# Delete Log
@app.route('/logs/delete/<path:filename>', methods=['POST'])
def delete_log(filename):
    # secure this in production!
    os.remove(os.path.join(CAN_DIR, filename))
    json_path = os.path.join(CAN_DIR, filename.replace('.csv','.json'))
    if os.path.exists(json_path):
        os.remove(json_path)
    flash(f'Deleted {filename}')
    return redirect(url_for('list_logs'))

# Delete All Logs
@app.route('/logs/delete_all', methods=['POST'])
def delete_all_logs():
    for fn in os.listdir(CAN_DIR):
        if fn.endswith('.csv') or fn.endswith('.json'):
            os.remove(os.path.join(CAN_DIR, fn))
    flash('All logs deleted')
    return redirect(url_for('list_logs'))

# ——— DBC routes ————————————————————————————————

@app.route('/dbc')
def list_dbcs():
    files = [fn for fn in os.listdir(DBC_DIR) if fn.endswith('.dbc')]
    return render_template('dbc.html', files=files)

@app.route('/dbc/upload', methods=['POST'])
def upload_dbc():
    f = request.files.get('dbc_file')
    if f and f.filename.endswith('.dbc'):
        f.save(os.path.join(DBC_DIR, f.filename))
        flash(f'Uploaded {f.filename}')
    else:
        flash('Invalid file')
    return redirect(url_for('list_dbcs'))

@app.route('/dbc/delete/<path:filename>', methods=['POST'])
def delete_dbc(filename):
    os.remove(os.path.join(DBC_DIR, filename))
    flash(f'Deleted {filename}')
    return redirect(url_for('list_dbcs'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# ——— Data Analysis Page ————————————————————————————————
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dash_bc
import plotly.graph_objs as go
import plotly.io as pio

pio.templates.default = 'plotly_dark'

@app.route('/data_analysis')
def data_analysis_page():
    return render_template('data_analysis.html')

# create Dash, tell it to use our Flask server under /data-analysis/
dash_app = Dash(
    __name__,
    server=app,
    url_base_pathname='/data_app/',
    external_stylesheets=[dash_bc.themes.CYBORG]
)

def list_csv_files():
    return sorted(f for f in os.listdir(CAN_DIR) if f.endswith('.csv'))

dash_app.layout = html.Div([
    # Dropdown to pick CSV file
    dcc.Dropdown(
        id='file-dropdown',
        options=[{'label':fn, 'value':fn} for fn in list_csv_files()],
        placeholder="Select a CSV file"
    ),
    # Dropdown to pick which column to plot (populated once file is chosen)
    dcc.Dropdown(id='column-dropdown', placeholder="Select data column"),
    # The graph
    dcc.Graph(id='time-series-plot')
])

# When a file is chosen, populate the columns dropdown
@dash_app.callback(
    Output('column-dropdown', 'options'),
    Input('file-dropdown', 'value')
)
def update_column_options(selected_file):
    if not selected_file:
        return []
    df = pd.read_csv(os.path.join(CAN_DIR, selected_file))
    # first column is time; we’ll offer all others for plotting
    cols = list(df.columns[1:])
    return [{'label': c, 'value': c} for c in cols]

# When both file and column are chosen, update the figure
@dash_app.callback(
    Output('time-series-plot', 'figure'),
    Input('file-dropdown', 'value'),
    Input('column-dropdown', 'value')
)
def update_graph(selected_file, selected_column):
    if not selected_file or not selected_column:
        return go.Figure()  # empty figure still picks up default

    df = pd.read_csv(os.path.join(CAN_DIR, selected_file))
    x = df.iloc[:,0]
    y = df[selected_column]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name=selected_column))
    fig.update_layout(
      title=f"{selected_column} over Time",
      xaxis_title=df.columns[0],
      yaxis_title=selected_column,
      # ← do NOT set a `template` here
      paper_bgcolor='rgba(0,0,0,0)',
      plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig