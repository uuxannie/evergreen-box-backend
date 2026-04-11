import sqlite3
import os
from datetime import datetime, date

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plant_presets (
            plant_name TEXT PRIMARY KEY,
            min_temp REAL, max_temp REAL,
            min_hum REAL, max_hum REAL,
            min_moist REAL
        )
    ''')

    # 3. camera snapshots db
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS camera_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_url TEXT NOT NULL,
            storage_type TEXT,
            captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            yolo_result TEXT,
            note TEXT
        )
    ''')
    
    # 4. device_logs table (Unified schema)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_latest_sensor_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_sensor_data(temp: float, hum: float, light: float, moist: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sensor_data (temperature, humidity, light, moisture) VALUES (?, ?, ?, ?)",
        (temp, hum, light, moist)
    )
    conn.commit()
    conn.close()

def get_history_data(limit=20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT temperature, humidity, light, moisture, timestamp 
            FROM sensor_data 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()

def get_action_counts():
    """Legacy function adapted to work with the new device_logs schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM device_logs WHERE target='water_pump' AND action='on' AND date(timestamp) = date('now')")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def log_device_action(target: str, action: str):
    """Logs a device command into the database with the current local timestamp."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO device_logs (target, action, timestamp) VALUES (?, ?, ?)",
        (target, action, now)
    )
    
    conn.commit()
    conn.close()

def get_today_device_stats() -> dict:
    """
    Counts how many times each device was turned 'on' today.
    Returns a dictionary like {"water_pump": 2, "fan": 1, "grow_light": 0}
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Required to access columns by name (row["target"])
    cursor = conn.cursor()
    
    today_str = date.today().strftime("%Y-%m-%d")
    
    cursor.execute('''
        SELECT target, COUNT(*) as count 
        FROM device_logs 
        WHERE action = 'on' AND timestamp LIKE ?
        GROUP BY target
    ''', (f"{today_str}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    stats = {
        "water_pump": 0,
        "fan": 0,
        "grow_light": 0
    }
    
    for row in rows:
        target_name = row["target"]
        if target_name in stats:
            stats[target_name] = row["count"]
            
    return stats