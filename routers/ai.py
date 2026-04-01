from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from services.openai_service import get_plant_response

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(req: ChatRequest):
    try:
        reply = get_plant_response(req.message)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))