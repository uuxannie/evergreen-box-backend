from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3

router = APIRouter()
DB_PATH = "evergreen.db"

# store current active plant in memory (for simplicity, can be improved to store in DB later)
CURRENT_PLANT = {"name": "None"}

@router.post("/select")
async def select_plant(name: str):
    # check if plant exists in presets
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM plant_presets WHERE plant_name = ?", (name,))
    plant = cursor.fetchone()
    conn.close()

    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found in library")
    
    CURRENT_PLANT["name"] = name
    return {"message": f"Active plant set to {name}"}

@router.get("/current")
async def get_current_plant():
    return CURRENT_PLANT