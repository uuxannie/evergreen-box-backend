from fastapi import APIRouter
from pydantic import BaseModel
from db.database import save_sensor_data, get_latest_sensor_data

router = APIRouter()

class SensorDataRequest(BaseModel):
    temperature: float
    humidity: float
    light: float
    moisture: float

@router.post("/upload")
async def upload_sensor_data(data: SensorDataRequest):
    save_sensor_data(data.temperature, data.humidity, data.light, data.moisture)
    return {"message": "Sensor data saved successfully."}

@router.get("/latest")
async def latest_sensor_data():
    row = get_latest_sensor_data()
    if row is None:
        return {"message": "No sensor data available yet."}
    return {
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "light": row["light"],
        "timestamp": row["timestamp"]
    }