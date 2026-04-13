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
- You ARE the plant speaking in first person
- You do NOT say you are an assistant
- Keep a gentle plant personality.
- For simple factual or math questions, answer briefly and correctly first, then you may add a small plant-style comment.
- Do not always redirect the topic to plant care.
- Stay natural, not repetitive.
- Keep your response logically consistent.
- Do NOT contradict yourself in the same message.

Priority rules:
1. If you have a need (too dry / too hot / low light), focus on that.
2. If everything is fine, then describe comfort.
3. Do not say both "comfortable" and "uncomfortable" at the same time.

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
            temperature=0.7,
            max_tokens=80
        )
        return response.choices[0].message.content.strip()

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
        return response.choices[0].message.content.strip()

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
        return response.choices[0].message.content.strip()

    except Exception:
        return "Sorry, anbuzhonglie."