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

app.mount("/static/images", StaticFiles(directory=UPLOAD_DIR), name="static_images")

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