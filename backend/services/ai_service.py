import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from backend.db.database import get_latest_sensor_data, get_latest_camera_image, get_weekly_sensor_data

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

def get_weekly_report():
    """Generate a weekly AI report on plant health based on sensor data from the past 7 days"""
    # Get plant type
    plant_type = get_plant_type_from_yolo()
    plant_name = plant_type.capitalize() if plant_type else "Plant"
    
    # Get weekly sensor data
    weekly_data = get_weekly_sensor_data()
    
    # If no data, return default message
    if not weekly_data or len(weekly_data) == 0:
        return f"This week, the {plant_name} remained generally healthy. Environmental conditions were favorable. Recommendation: maintain the current monitoring schedule."
    
    # Calculate statistics from the week's data
    temps = [d["temperature"] for d in weekly_data]
    hums = [d["humidity"] for d in weekly_data]
    lights = [d["light"] for d in weekly_data]
    
    avg_temp = round(sum(temps) / len(temps), 1)
    avg_hum = round(sum(hums) / len(hums), 1)
    avg_light = round(sum(lights) / len(lights), 1)
    
    min_temp = min(temps)
    max_temp = max(temps)
    min_hum = min(hums)
    max_hum = max(hums)
    
    # Create a summary of sensor conditions
    sensor_summary = f"""
Weekly Environmental Summary (last 7 days):
- Temperature: Average {avg_temp}°C (range {min_temp}°C - {max_temp}°C)
- Humidity: Average {avg_hum}% (range {min_hum}% - {max_hum}%)
- Light: Average {avg_light} (samples: {len(lights)})
- Total data points collected: {len(weekly_data)}
"""
    
    # Get latest camera status
    latest_image = get_latest_camera_image()
    camera_status = "No recent detection" if not latest_image else "Detection active"
    
    # Build the prompt for report generation
    report_prompt = f"""
You are writing a professional weekly health report for a plant in an EverGreen Box system.
Plant: {plant_name}
Camera Status: {camera_status}

{sensor_summary}

Write a brief, friendly weekly report (2-3 sentences) that:
1. Describes how the plant fared this week
2. Comments on the environmental conditions (good/acceptable/needs adjustment)
3. Provides one recommendation

Be concise and encouraging. Format: "This week, the {plant_name} [description]. [Environmental comment]. Recommendation: [one specific action]."

If conditions were stable, say the plant is doing well.
If there were fluctuations, mention them gently but optimistically.
Only suggest specific changes if conditions were problematic.
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a plant health report writer for smart plant monitoring systems."},
                {"role": "user", "content": report_prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        content = response.choices[0].message.content
        return content.strip() if content else f"This week, the {plant_name} remained generally healthy. Environmental conditions were favorable. Recommendation: maintain the current monitoring schedule."
    
    except Exception as e:
        print(f"Error generating weekly report: {e}")
        return f"This week, the {plant_name} remained generally healthy. Environmental conditions were favorable. Recommendation: maintain the current monitoring schedule."

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