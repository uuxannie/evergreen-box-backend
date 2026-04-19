from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from routers import ai
from db.database import init_db
from routers import sensor
from routers import device
from routers import camera
from routers.camera import UPLOAD_DIR
from scheduler import init_scheduler, shutdown_scheduler
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database and scheduler
    logger.info("[STARTUP] Starting EverGreen Box Backend...")
    init_db()
    logger.info("[STARTUP] Database initialized.")
    init_scheduler()
    logger.info("[STARTUP] Background scheduler initialized.")
    
    yield  # Application runs here
    
    # Shutdown: Cleanup scheduler
    logger.info("[SHUTDOWN] Shutting down EverGreen Box Backend...")
    shutdown_scheduler()
    logger.info("[SHUTDOWN] Server shutdown complete.")

app = FastAPI(title="EverGreen Box API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.staticfiles import StaticFiles

RENDER_DISK_BASE = "/var/lib/data"
LOCAL_STATIC_BASE = os.path.join(os.getcwd(), "static")

if os.path.exists(RENDER_DISK_BASE):
    static_dir = RENDER_DISK_BASE
    logger.info(f"[SYSTEM] Running in cloud. Mounting persistent disk: {static_dir}")
else:
    static_dir = LOCAL_STATIC_BASE
    os.makedirs(static_dir, exist_ok=True)
    logger.info(f"[SYSTEM] Running locally. Mounting directory: {static_dir}")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(ai.router, prefix="/api", tags=["AI"])
app.include_router(sensor.router, prefix="/api/sensor", tags=["Sensor"])
app.include_router(device.router, prefix="/api/device", tags=["Device"])
app.include_router(camera.router, prefix="/api/camera", tags=["Camera"])

@app.get("/")
def root():
    return {"message": "EverGreen Box backend is running!"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)