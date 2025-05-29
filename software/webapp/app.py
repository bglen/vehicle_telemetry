from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash
import os, json

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
