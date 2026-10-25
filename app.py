import os
import json
import sqlite3
import subprocess
import datetime
import time
import requests
from flask import Flask, render_template, request, jsonify, Response
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
DB_PATH = os.path.join("data", "speedtest.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ping REAL,
            download REAL,
            upload REAL,
            is_ok INTEGER,
            is_full_test INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Default settings
    defaults = {
        "interval_minutes": "30",
        "threshold_mbps": "100",
        "full_test_times": "00:00,06:00,12:00,18:00",
        "retention_days": "30"
    }
    
    for key, value in defaults.items():
        cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
        
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def cleanup_old_results():
    retention_days = int(get_setting("retention_days"))
    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM results WHERE timestamp < ?', (cutoff.strftime("%Y-%m-%d %H:%M:%S"),))
    conn.commit()
    conn.close()

def quick_check():
    cleanup_old_results()
    threshold = float(get_setting("threshold_mbps"))
    download_url = "https://speed.hetzner.de/100MB.bin"
    
    try:
        start_time = time.time()
        response = requests.get(download_url, stream=True, timeout=10)
        
        total_bytes = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                total_bytes += len(chunk)
                
        end_time = time.time()
        duration = end_time - start_time
        
        if duration > 0:
            download_mbps = (total_bytes * 8) / 1000000 / duration
        else:
            download_mbps = 0
            
        is_ok = 1 if download_mbps >= threshold else 0
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO results (timestamp, ping, download, upload, is_ok, is_full_test) VALUES (?, ?, ?, ?, ?, ?)',
                       (timestamp, 0, download_mbps, 0, is_ok, 0))
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Quick check failed: {e}")

def run_full_speedtest():
    cleanup_old_results()
    threshold = float(get_setting("threshold_mbps"))
    
    try:
        result = subprocess.run(
            ["speedtest", "--accept-license", "--accept-gdpr", "-f", "json"],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        
        # Convert bytes per second to Mbps
        download_mbps = data['download']['bandwidth'] * 8 / 1000000
        upload_mbps = data['upload']['bandwidth'] * 8 / 1000000
        ping = data['ping']['latency']
        
        is_ok = 1 if download_mbps >= threshold else 0
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO results (timestamp, ping, download, upload, is_ok, is_full_test) VALUES (?, ?, ?, ?, ?, ?)',
                       (timestamp, ping, download_mbps, upload_mbps, is_ok, 1))
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Speedtest failed: {e}")

scheduler = BackgroundScheduler()

def schedule_jobs():
    scheduler.remove_all_jobs()
    
    interval = int(get_setting("interval_minutes"))
    scheduler.add_job(quick_check, 'interval', minutes=interval, id='standard_test')
    
    times = get_setting("full_test_times").split(',')
    for t in times:
        t = t.strip()
        if t:
            hour, minute = t.split(':')
            scheduler.add_job(run_full_speedtest, 'cron', hour=int(hour), minute=int(minute))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/results')
def api_results():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Fetch last 24 hours
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=24)
    cursor.execute('SELECT timestamp, ping, download, upload, is_ok, is_full_test FROM results WHERE timestamp >= ? ORDER BY timestamp ASC', (cutoff.strftime("%Y-%m-%d %H:%M:%S"),))
    rows = cursor.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            "timestamp": row[0],
            "ping": row[1],
            "download": row[2],
            "upload": row[3],
            "is_ok": row[4],
            "is_full_test": row[5]
        })
    return jsonify(data)

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'POST':
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for key, value in data.items():
            cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (str(value), key))
        conn.commit()
        conn.close()
        schedule_jobs()
        return jsonify({"status": "success"})
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM settings')
    settings = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return jsonify(settings)

@app.route('/api/export')
def export_csv():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, ping, download, upload, is_ok, is_full_test FROM results ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    conn.close()
    
    csv_data = "Timestamp,Ping(ms),Download(Mbps),Upload(Mbps),Status,TestType\n"
    for row in rows:
        status = "OK" if row[4] else "BELOW LIMIT"
        test_type = "FULL" if row[5] else "STANDARD"
        csv_data += f"{row[0]},{row[1]:.2f},{row[2]:.2f},{row[3]:.2f},{status},{test_type}\n"
        
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=speedtest_results.csv"}
    )

@app.route('/api/delete_all', methods=['POST'])
def delete_all():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM results')
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    if not os.path.exists("data"):
        os.makedirs("data")
    init_db()
    schedule_jobs()
    scheduler.start()
    app.run(host='0.0.0.0', port=8080)