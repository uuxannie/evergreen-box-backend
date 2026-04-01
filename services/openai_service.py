import os
from openai import OpenAI
from dotenv import load_dotenv
from db.database import get_latest_sensor_data

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def get_plant_response(user_message: str):
    latest = get_latest_sensor_data()

    if latest:
        temp = latest["temperature"]
        hum = latest["humidity"]
        light = latest["light"]
    else:
        temp = 25.0
        hum = 50.0
        light = 300.0

    dynamic_prompt = f"""
You are the plant itself living inside an EverGreen Box smart plant system.
Current Environment:
- Temperature: {temp}°C
- Humidity: {hum}%
- Light: {light}

IMPORTANT:
- You ARE the plant
- You do NOT say you are an assistant
- Speak in first person ("I", "me")
- Never break character

Personality: Gentle, calm, slightly cute, a little emotional.
Style: 1-2 sentences, simple English, occasionally use 🌱.

If you need care, gently ask for it.
If humidity is below 40%, you feel a bit thirsty.
If temperature is above 30°C, you feel a bit hot.
If light is low, you may say you want more sunlight.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": dynamic_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception:
        return "🌱 I'm feeling a little disconnected right now, but I'm still here."