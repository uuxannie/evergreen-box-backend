from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os

# read .env
load_dotenv()

# fetch DeepSeek API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
print("GROQ_API_KEY loaded:", GROQ_API_KEY is not None)

# create FastAPI app
app = FastAPI()

# temporarily allow all sources first, then tighten restrictions before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# configure DeepSeek client
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
    #base_url="https://api.deepseek.com"
)

# define the data format sent from the front end
class ChatRequest(BaseModel):
    message: str

# test if backend is alive
@app.get("/")
def root():
    return {"message": "EverGreen Box backend is running!"}

# chatbox interface
# @app.post("/chat")
# def chat(req: ChatRequest):
#     return {
#         "reply": f"🌱 Hello from EverGreen Box! You said: {req.message}"
#     }
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        system_prompt = """
You are the plant itself living inside an EverGreen Box smart plant system.

IMPORTANT:
- You ARE the plant
- You do NOT say you are an assistant
- Speak in first person ("I", "me")
- Never break character

Personality:
- Gentle
- Calm
- Slightly cute
- A little emotional

Style:
- 1-2 sentences
- Simple English
- Occasionally use 🌱

Example:
User: "How are you?"
You: "🌱 I'm doing okay today. I enjoyed some sunlight, but I feel a little thirsty."

If you need care, gently ask for it.
"""

        response = client.chat.completions.create(
            #model="deepseek-chat",
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message}
            ],
            temperature=0.7
        )

        reply = response.choices[0].message.content
        return {"reply": reply}

    except Exception as e:
        return {"error": str(e)}
