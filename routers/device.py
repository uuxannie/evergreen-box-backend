from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from datetime import datetime
from db.database import log_device_action, get_today_device_stats
from db.database import update_state_in_db, get_state_from_db

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

class DeviceStateUpdate(BaseModel):
    target: Literal["water_pump", "fan", "grow_light"]
    action: Literal["on", "off"]

@router.post("/set_state")
async def set_device_state(command: DeviceStateUpdate) -> dict:
    try:
        # write the new state to SQLite database
        update_state_in_db(command.target, command.action)
    except Exception as e:
        print(f"[DB ERROR] Failed to update state: {e}")
        raise HTTPException(status_code=500, detail="Failed to update device state.")
    
    print(f"[MAILBOX UPDATE] Frontend requested: {command.target} -> {command.action}")
    
    return {
        "status": "success",
        "message": f"Command received. {command.target} will be turned {command.action} shortly."
    }

@router.get("/current_state")
async def get_current_state() -> dict:
    try:
        # from SQLite read the newest state of all devices and return to ESP?? whenever asked
        return get_state_from_db()
    except Exception as e:
        print(f"[DB ERROR] Failed to get state: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve device state.")