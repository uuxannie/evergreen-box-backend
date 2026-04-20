# EverGreen Box - Plant Monitoring System

## 📁 Project Structure

```
EverGreenBox/
├── backend/                 # All backend code
│   ├── main.py             # FastAPI entry point
│   ├── scheduler.py        # Scheduled tasks
│   ├── requirements.txt    # Python dependencies
│   ├── db/                 # Database models and initialization
│   │   └── database.py
│   ├── routers/            # API route handlers
│   │   ├── ai.py          # AI/GROQ endpoints
│   │   ├── camera.py      # Camera/timelapse endpoints
│   │   ├── device.py      # Device management
│   │   ├── plant.py       # Plant data
│   │   └── sensor.py      # Sensor data
│   ├── services/           # Business logic
│   │   ├── openai_service.py  # GROQ API integration
│   │   └── timelapse_service.py
│   ├── static/             # Static files (images, videos)
│   └── chat-test.html
├── webcam/                 # Local webcam monitoring (not synced to Git)
│   ├── yolo_cam.py        # Real-time YOLO detection
│   └── requirements.txt    # Webcam-specific dependencies
├── .env                    # Local environment variables (NOT in Git)
├── .env.example            # Template for environment variables
├── .gitignore              # Git ignore rules
├── render.yaml             # Render deployment configuration
└── README.md               # This file
```

## 🚀 Development Setup

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Server runs at: `http://localhost:8000`

### Webcam Monitoring (Local Only)

```bash
cd webcam
source .venv/bin/activate
python yolo_cam.py
```

## 📋 Environment Variables

Create `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
YOUR_WHATSAPP_NUMBER=whatsapp:+85297050549
RENDER_BACKEND_URL=https://evergreen-box-backend.onrender.com
```

## 🌐 API Endpoints

- `/docs` - Swagger UI (interactive API docs)
- `/api/camera/upload-image` - Upload plant images
- `/api/camera/generate-demo-video` - Generate timelapse video
- `/api/ai/*` - AI/GROQ endpoints
- `/api/device/*` - Device management
- `/api/sensor/*` - Sensor data

## 🚢 Deployment (Render)

1. Connect this GitHub repo to Render
2. Set deployment command to: `cd backend && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000`
3. Add environment variables in Render dashboard (from .env.example)
4. Deploy!

## 📝 Notes

- `webcam/` is excluded from Git (for local development only)
- `.env` is excluded from Git (keep secrets safe)
- Backend code is fully contained in `backend/` directory
- Render deployment uses `/var/lib/data` for persistent storage
