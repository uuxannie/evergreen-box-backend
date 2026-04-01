from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from services.openai_service import get_plant_response
import time

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(req: ChatRequest):
    start_time = time.time()
    try:
        print(f"Received message: {req.message}")
        reply = get_plant_response(req.message)
        elapsed = time.time() - start_time
        print(f"Chat reply generated in {elapsed:.2f} seconds")
        return {"reply": reply}
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Chat failed after {elapsed:.2f} seconds: {e}")
        raise HTTPException(status_code=500, detail=str(e))