from datetime import datetime
import sqlite3

DB_PATH = "evergreen.db"

def init_db():
    """初始化数据库，创建传感器数据表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature REAL,
            humidity REAL,
            light REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_latest_sensor_data():
    """获取最新的一条传感器记录"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 这样可以像字典一样取值
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row

def save_sensor_data(temp: float, hum: float, light: float):
    """保存数据（供后续 sensor_service 调用）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sensor_data (temperature, humidity, light) VALUES (?, ?, ?)",
        (temp, hum, light)
    )
    conn.commit()
    conn.close()