from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from datetime import datetime
from db.database import log_device_action, get_today_device_stats

router = APIRouter()

class DeviceLogPayload(BaseModel):
    target: Literal["water_pump", "fan", "grow_light"]
    action: Literal["on", "off"]

@router.post("/upload_log")
async def upload_device_log(payload: DeviceLogPayload) -> dict: 
    try:
        log_device_action(payload.target, payload.action)
    except Exception as e:
        print(f"[DB ERROR] Failed to log action: {e}")
        raise HTTPException(status_code=500, detail="Failed to log device action to the database.")

    print(f"[HARDWARE] Log received from ESP8266: {payload.target} -> {payload.action}")

    return {
        "status": "success", 
        "message": f"Log recorded: {payload.target.replace('_', ' ').title()} turned {payload.action}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@router.get("/stats")
async def device_stats() -> dict:
    try:
        # Aggregate today's device action counts from the SQLite database
        stats = get_today_device_stats()
        
        # in case there are no logs for today, return zero counts for all 
        if stats is None:
            return {"water_pump": 0, "grow_light": 0, "fan": 0}
            
        return stats
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve device statistics.")