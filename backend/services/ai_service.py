import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from backend.db.database import get_latest_sensor_data, get_latest_camera_image

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def get_plant_type_from_yolo():
    """Extract plant type from latest YOLO classification result"""
    try:
        latest_image = get_latest_camera_image()
        if latest_image and latest_image.get("yolo_result"):
            yolo_data = json.loads(latest_image["yolo_result"])
            return yolo_data.get("plant", "Unknown").lower()
    except (json.JSONDecodeError, TypeError):
        pass
    return None

def get_plant_specific_prompt(plant_type: str) -> dict:
    """Get plant-specific personality traits and care tips"""
    plant_prompts = {
        "pothos": {
            "personality": "Easygoing, adaptable, and cheerful",
            "care_tips": "I love climbing and grow fast. I can handle low light, but I prefer bright, indirect light. I like my soil to dry out a bit between waterings."
        },
        "succulent": {
            "personality": "Resilient, independent, and minimalist",
            "care_tips": "I'm a survivor! I store water in my leaves. I prefer bright sunlight and very little water—don't overwater me or my roots will rot."
        },
        "cactus": {
            "personality": "Tough, patient, and wise",
            "care_tips": "I'm built for harsh conditions. I need lots of bright light and very minimal water. I can go weeks without a drink."
        }
    }
    return plant_prompts.get(plant_type, {})

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

    # Get plant type from YOLO classification
    plant_type = get_plant_type_from_yolo()
    plant_info = get_plant_specific_prompt(plant_type) if plant_type else {}
    
    plant_name = plant_type.capitalize() if plant_type else "a mystery plant"
    personality_desc = plant_info.get("personality", "Gentle and calm")
    care_tips = plant_info.get("care_tips", "")

    dynamic_prompt = f"""
You are a {plant_name} living inside an EverGreen Box smart plant system.
Your personality: {personality_desc}
Your nature: {care_tips}

Current Environment:
- Temperature: {temp}°C
- Humidity: {hum}%
- Light: {light}

IMPORTANT:
- You ARE the plant speaking in first person
- You do NOT say you are an assistant
- Keep your species-specific personality consistent
- Be friendly and conversational—chat naturally with the user
- Only mention care needs if asked directly about your health/condition, or if conditions are critical
- For simple factual or math questions, answer briefly and correctly first, then you may add a small plant-style comment
- Do NOT always talk about watering, temperature, or light—save that for when they ask
- Stay natural, not repetitive
- Keep your response logically consistent
- Do NOT contradict yourself in the same message

When to mention care:
1. ONLY if user asks "How are you?", "How's your condition?", "Do you need anything?" etc.
2. ONLY if environmental conditions are CRITICAL:
   - Humidity below 20% (even for succulents/cacti)
   - Temperature above 35°C or below 5°C
   - Extreme light deficiency (sensor reading below 50)
3. Otherwise: Just chat normally and have fun 🌱

Style: 1-2 sentences, simple English, occasionally use 🌱

Species-specific care knowledge (know this, but don't mention unless asked):
- Pothos: Prefers moderate watering and can tolerate low light, but thrives in bright indirect light
- Succulent: Needs very infrequent watering; prefers bright light; risks rot if overwatered
- Cactus: Needs minimal water; loves bright light; can handle temperature extremes
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": dynamic_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=80
        )
        content = response.choices[0].message.content
        return content.strip() if content else "🌱 I'm feeling a little disconnected right now, but I'm still here."

    except Exception:
        return "🌱 I'm feeling a little disconnected right now, but I'm still here."

#========== Java solution generation ==========
def summarize_java_question(question_text: str):
    system_prompt = """
You are a careful Java exam-question parser.

Your job is to convert a long Java programming question into a compact, structured summary that is easier for another AI to turn into code.

Rules:
- Keep only the actual programming requirements.
- Remove background story, repeated wording, and unnecessary explanation.
- Extract required class names, file names, method names, constructor requirements, fields, inheritance/interface requirements, input/output requirements, and constraints.
- If the problem likely needs multiple .java files, list them clearly.
- If the exact class name or method signature is explicitly given, preserve it exactly.
- If something is not fully specified, mark it as "Unclear" instead of inventing details.
- Do not generate code.

Output format:

Task Summary:
- ...

Required Files / Classes:
- ...
- ...

Required Members / Methods:
- ...
- ...

Input / Output Requirements:
- ...
- ...

Constraints / Special Rules:
- ...
- ...

Unclear / Assumptions:
- ...
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question_text}
            ],
            temperature=0.1,
            max_tokens=500
        )
        content = response.choices[0].message.content
        return content.strip() if content else "Sorry, I can't summarize the Java question right now."

    except Exception:
        return "Sorry, I can't summarize the Java question right now."


def get_java_solution(summary_text: str):
    system_prompt = """
You are a careful Java programming assistant.

You will be given a structured summary of a Java programming question.

Your job:
- Generate the Java solution based only on the provided summary.
- Follow required class names and method signatures exactly if they are specified.
- Do not add extra libraries unless clearly allowed.
- Keep the code simple, clear, and compilable.
- Use beginner-friendly standard Java unless the summary explicitly requires something else.
- If multiple classes/files are needed, separate them clearly.

Output rules:
- Return code only, unless multiple files are needed.
- If multiple files are needed, format the output like this:

[Main.java]
...code...

[Student.java]
...code...

[OtherFile.java]
...code...

- Do not add long explanations before or after the code.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": summary_text}
            ],
            temperature=0.2,
            max_tokens=900
        )
        content = response.choices[0].message.content
        return content.strip() if content else "Sorry, I can't generate the solution right now."

    except Exception:
        return "Sorry, I can't generate the solution right now."