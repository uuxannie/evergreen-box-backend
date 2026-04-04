from datetime import datetime
import sqlite3

DB_PATH = "evergreen.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 1. sensor db
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature REAL,
            humidity REAL,
            light REAL,
            moisture REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. plant presets db
    cursor.execute('''CREATE TABLE IF NOT EXISTS plant_presets (
        plant_name TEXT PRIMARY KEY,
        min_temp REAL, max_temp REAL,
        min_hum REAL, max_hum REAL,
        min_moist REAL)''')

    # 3. device logs db
    cursor.execute('''CREATE TABLE IF NOT EXISTS device_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT, -- 'WATERING' 或 'VENTILATION'
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_latest_sensor_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row

def save_sensor_data(temp: float, hum: float, light: float, moist: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sensor_data (temperature, humidity, light, moisture) VALUES (?, ?, ?, ?)",
        (temp, hum, light, moist)
    )
    conn.commit()
    conn.close()

def get_action_counts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # record today's watering count
    cursor.execute("SELECT COUNT(*) FROM device_logs WHERE action_type='WATERING' AND date(timestamp) = date('now')")
    count = cursor.fetchone()[0]
    conn.close()
    return count