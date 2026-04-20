import sqlite3
import os
from datetime import datetime, date
from contextlib import contextmanager

RENDER_DISK_BASE = "/var/lib/data"

# dinamically set the database path
if os.path.exists(RENDER_DISK_BASE):
    DB_PATH = os.path.join(RENDER_DISK_BASE, "evergreen.db")
else:
    DB_PATH = "evergreen.db"
    
# dinamically set image Storage Path)
if os.path.exists(RENDER_DISK_BASE):
    IMAGE_DIR = os.path.join(RENDER_DISK_BASE, "images")
else:
    IMAGE_DIR = "static/images"

@contextmanager
def get_db_connection():
    """Context manager for database connections with proper error handling"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. sensor db - with constraints for data integrity
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                light REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                CHECK (temperature >= -50 AND temperature <= 60),
                CHECK (humidity >= 0 AND humidity <= 100),
                CHECK (light >= 0)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_data(timestamp DESC)')

        # 2. plant presets db - with constraints
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plant_presets (
                plant_name TEXT PRIMARY KEY NOT NULL,
                min_temp REAL NOT NULL,
                max_temp REAL NOT NULL,
                min_hum REAL NOT NULL,
                max_hum REAL NOT NULL,
                min_moist REAL NOT NULL,
                CHECK (min_temp < max_temp),
                CHECK (min_hum < max_hum),
                CHECK (min_moist >= 0)
            )
        ''')

        # 3. camera snapshots db - with not null and indexing
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS camera_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_url TEXT NOT NULL,
                storage_type TEXT NOT NULL DEFAULT 'local',
                captured_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                yolo_result TEXT,
                note TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_camera_captured ON camera_images(captured_at DESC)')
        
        # 4. device_logs table (Unified schema) - with constraints
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                CHECK (target IN ('water_pump', 'fan', 'grow_light')),
                CHECK (action IN ('on', 'off'))
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_logs_date ON device_logs(target, date(timestamp))')
        
        # 5. device_state table - with constraints
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_state (
                target TEXT PRIMARY KEY NOT NULL,
                action TEXT NOT NULL,
                CHECK (target IN ('water_pump', 'fan', 'grow_light')),
                CHECK (action IN ('on', 'off'))
            )
        ''')
        
        # Insert initial states
        cursor.executemany('''
            INSERT OR IGNORE INTO device_state (target, action)
            VALUES (?, ?)
        ''', [("water_pump", "off"), ("fan", "off"), ("grow_light", "off")])

        conn.commit()

def get_latest_sensor_data():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

def save_sensor_data(temp: float, hum: float, light: float):
    """Save sensor data with validation and transaction support"""
    # Input validation
    if not (-50 <= temp <= 60):
        raise ValueError(f"Temperature {temp} out of valid range [-50, 60]")
    if not (0 <= hum <= 100):
        raise ValueError(f"Humidity {hum} out of valid range [0, 100]")
    if light < 0:
        raise ValueError(f"Light {light} cannot be negative")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sensor_data (temperature, humidity, light) VALUES (?, ?, ?)",
                (temp, hum, light)
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error while saving sensor data: {e}")
        raise

def get_history_data(limit=20):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT temperature, humidity, light, timestamp 
                FROM sensor_data 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

def get_weekly_sensor_data():
    """Get all sensor data from the past 7 days"""
    try:
        from datetime import timedelta
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get data from the past 7 days
            cursor.execute("""
                SELECT temperature, humidity, light, timestamp 
                FROM sensor_data 
                WHERE timestamp >= datetime('now', '-7 days')
                ORDER BY timestamp DESC
            """)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

def get_action_counts():
    """Legacy function adapted to work with the new device_logs schema."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM device_logs WHERE target='water_pump' AND action='on' AND date(timestamp) = date('now')")
            result = cursor.fetchone()
            return result[0] if result else 0
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return 0

def log_device_action(target: str, action: str):
    """Logs a device command into the database with validation and transaction support"""
    # Input validation
    valid_targets = {'water_pump', 'fan', 'grow_light'}
    valid_actions = {'on', 'off'}
    
    if target not in valid_targets:
        raise ValueError(f"Invalid target: {target}. Must be one of {valid_targets}")
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                "INSERT INTO device_logs (target, action, timestamp) VALUES (?, ?, ?)",
                (target, action, now)
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error while logging device action: {e}")
        raise

def get_today_device_stats() -> dict:
    """
    Counts how many times each device was turned 'on' today.
    Returns a dictionary like {"water_pump": 2, "fan": 1, "grow_light": 0}
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            today_str = date.today().strftime("%Y-%m-%d")
            
            cursor.execute('''
                SELECT target, COUNT(*) as count 
                FROM device_logs 
                WHERE action = 'on' AND timestamp LIKE ?
                GROUP BY target
            ''', (f"{today_str}%",))
            
            rows = cursor.fetchall()
            
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
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return {"water_pump": 0, "fan": 0, "grow_light": 0}

def save_camera_image(image_url: str, storage_type: str = "local", yolo_result: str = None):
    """Saves a new camera image record with validation and transaction support"""
    if not image_url or len(image_url.strip()) == 0:
        raise ValueError("image_url cannot be empty")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO camera_images (image_url, storage_type, yolo_result) VALUES (?, ?, ?)",
                (image_url, storage_type, yolo_result)
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error while saving image: {e}")
        raise

def get_latest_camera_image():
    """Fetches the latest camera image record from the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM camera_images ORDER BY captured_at DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error while fetching latest image: {e}")
        return None

def update_state_in_db(target: str, action: str):
    """Updates device state with validation"""
    valid_targets = {'water_pump', 'fan', 'grow_light'}
    valid_actions = {'on', 'off'}
    
    if target not in valid_targets:
        raise ValueError(f"Invalid target: {target}. Must be one of {valid_targets}")
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE device_state 
                SET action = ? 
                WHERE target = ?
            ''', (action, target))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error while updating state: {e}")
        raise

def get_state_from_db() -> dict:
    """Retrieves current device states"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT target, action FROM device_state")
            rows = cursor.fetchall()
            # Convert [(water_pump, off), (fan, on)] into a dictionary and return it.
            return {row["target"]: row["action"] for row in rows}
    except sqlite3.Error as e:
        print(f"Database error while retrieving state: {e}")
        return {}