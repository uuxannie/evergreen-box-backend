from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Literal
from datetime import datetime
import traceback
from db.database import log_device_action, get_today_device_stats
from db.database import update_state_in_db, get_state_from_db

router = APIRouter()

class DeviceCommand(BaseModel):
    """Device command payload - shared for both log and state update"""
    target: Literal["water_pump", "fan", "grow_light"]
    action: Literal["on", "off"]

class DeviceLogResponse(BaseModel):
    """Response for device log upload"""
    status: str
    message: str
    timestamp: str

class DeviceStatsResponse(BaseModel):
    """Device statistics for today"""
    water_pump: int = 0
    fan: int = 0
    grow_light: int = 0

class DeviceStateResponse(BaseModel):
    """Current state of all devices"""
    water_pump: str
    fan: str
    grow_light: str

class CommandResponse(BaseModel):
    """Response for device command"""
    status: str
    message: str


@router.post("/upload_log", response_model=DeviceLogResponse, status_code=status.HTTP_201_CREATED)
async def upload_device_log(payload: DeviceCommand) -> DeviceLogResponse:
    """
    Record a device action log from hardware (e.g., ESP8266).
    
    Args:
        payload: Device target (water_pump/fan/grow_light) and action (on/off)
        
    Returns:
        DeviceLogResponse with status, message, and timestamp
        
    Raises:
        HTTPException: If database operation fails
    """
    try:
        log_device_action(payload.target, payload.action)
    except ValueError as e:
        print(f"[VALIDATION ERROR] Invalid input: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"[DB ERROR] Failed to log action: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log device action to the database."
        )

    print(f"[HARDWARE] Log received from ESP8266: {payload.target} -> {payload.action}")

    return DeviceLogResponse(
        status="success",
        message=f"Log recorded: {payload.target.replace('_', ' ').title()} turned {payload.action}",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

@router.get("/stats", response_model=DeviceStatsResponse)
async def device_stats() -> DeviceStatsResponse:
    """
    Get today's device action statistics.
    
    Returns:
        DeviceStatsResponse with counts of how many times each device was turned 'on'
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        stats = get_today_device_stats()
        
        # Ensure valid response even if stats is empty
        if stats is None:
            stats = {"water_pump": 0, "grow_light": 0, "fan": 0}
            
        return DeviceStatsResponse(**stats)
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch stats: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device statistics."
        )

class DeviceStateUpdate(BaseModel):
    target: Literal["water_pump", "fan", "grow_light"]
    action: Literal["on", "off"]

@router.post("/set_state", response_model=CommandResponse, status_code=status.HTTP_200_OK)
async def set_device_state(command: DeviceCommand) -> CommandResponse:
    """
    Set the state of a device. This updates the mailbox for ESP8266 to read.
    
    Args:
        command: Device target (water_pump/fan/grow_light) and desired action (on/off)
        
    Returns:
        CommandResponse with status and message
        
    Raises:
        HTTPException: If database update fails
    """
    try:
        update_state_in_db(command.target, command.action)
    except ValueError as e:
        print(f"[VALIDATION ERROR] Invalid input: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"[DB ERROR] Failed to update state: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device state."
        )
    
    print(f"[MAILBOX UPDATE] Frontend requested: {command.target} -> {command.action}")
    
    return CommandResponse(
        status="success",
        message=f"Command received. {command.target} will be turned {command.action} shortly."
    )

@router.get("/current_state", response_model=DeviceStateResponse)
async def get_current_state() -> DeviceStateResponse:
    """
    Get the current state of all devices.
    
    Returns:
        DeviceStateResponse with current state (on/off) for each device
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        state = get_state_from_db()
        return DeviceStateResponse(**state)
    except Exception as e:
        print(f"[DB ERROR] Failed to get state: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device state."
        )