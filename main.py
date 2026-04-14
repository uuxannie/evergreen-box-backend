from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import ai
from db.database import init_db
from routers import sensor
from routers import device
from routers import camera
from routers.camera import UPLOAD_DIR
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialized.")
    yield  # this is where the app runs
    # execute shutdown code here if needed
    print("Server is shutting down...")

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
    print(f"[SYSTEM] 正在云端运行，挂载硬盘: {static_dir}")
else:
    static_dir = LOCAL_STATIC_BASE
    os.makedirs(static_dir, exist_ok=True)
    print(f"[SYSTEM] 正在本地运行，挂载目录: {static_dir}")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

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