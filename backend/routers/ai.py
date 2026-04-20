from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from backend.services.ai_service import get_plant_response
from backend.services.ai_service import summarize_java_question, get_java_solution
import time

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class JavaSummaryRequest(BaseModel):
    question_text: str

class JavaSolveRequest(BaseModel):
    summary_text: str

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
    
@router.post("/java/summarize")
def java_summarize(request: JavaSummaryRequest):
    summary = summarize_java_question(request.question_text)
    return {"summary": summary}

@router.post("/java/solve")
def java_solve(request: JavaSolveRequest):
    solution = get_java_solution(request.summary_text)
    return {"solution": solution}