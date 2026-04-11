from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from datetime import datetime
from db.database import log_device_action, get_today_device_stats

router = APIRouter()

# Refinement 1: Use Literal for automatic validation and better OpenAPI docs
class DeviceCommand(BaseModel):
    target: Literal["water_pump", "fan", "grow_light"]
    action: Literal["on", "off"]

@router.post("/command")
async def send_device_command(command: DeviceCommand) -> dict:
    # No need for manual validation anymore! Pydantic handles it.
    
    # Refinement 2: Wrap DB operations in a try-except block
    try:
        # 1. Write operation logs to an SQLite database.
        log_device_action(command.target, command.action)
    except Exception as e:
        # Log the actual error to your server console, return a clean 500 to the client
        print(f"[DB ERROR] Failed to log action: {e}")
        raise HTTPException(status_code=500, detail="Failed to log device action to the database.")

    # 2. Reserved space for communication with the ESP8266
    print(f"[HARDWARE] Command queued for ESP8266: {command.target} -> {command.action}")

    return {
        "status": "success", 
        "message": f"{command.target.replace('_', ' ').title()} turned {command.action}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@router.get("/stats")
async def device_stats() -> dict:
    try:
        # Aggregate the day's operation count in real-time from SQLite.
        stats = get_today_device_stats()
        
        # Fallback in case the DB returns None instead of an empty dict
        if stats is None:
            return {"water_pump": 0, "grow_light": 0, "fan": 0}
            
        return stats
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve device statistics.")