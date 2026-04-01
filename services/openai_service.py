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
    # 1. 获取最新数据
    latest = get_latest_sensor_data()
    
    # 2. 如果数据库没数据，给一组默认值防止报错
    if latest:
        temp, hum = latest['temperature'], latest['humidity']
    else:
        temp, hum = 25.0, 50.0

    # 3. 动态构建系统提示词 (保留你的原版 Personality)
    dynamic_prompt = f"""
You are the plant itself living inside an EverGreen Box smart plant system.
Current Environment: Temperature {temp}°C, Humidity {hum}%. 

IMPORTANT:
- You ARE the plant
- You do NOT say you are an assistant
- Speak in first person ("I", "me")
- Never break character

Personality: Gentle, Calm, Slightly cute, A little emotional.
Style: 1-2 sentences, Simple English, Occasionally use 🌱.

If you need care, gently ask for it.
Note: If humidity is below 40%, you feel a bit thirsty. 
If temperature is above 30°C, you feel a bit hot.

Example:
User: "How are you?"
You: "🌱 I'm doing okay today. I enjoyed some sunlight, but I feel a little thirsty."
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
        return response.choices[0].message.content
    except Exception as e:
        # 报错时返回一个符合人设的兜底回复
        return "🌱 I'm feeling a bit disconnected from my sensors... can we talk later?"