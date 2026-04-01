from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ai
from db.database import init_db
from routers import sensor

app = FastAPI(title="EverGreen Box API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai.router, prefix="/api", tags=["AI"])

app.include_router(sensor.router, prefix="/api/sensor", tags=["Sensor"])

@app.on_event("startup")
def startup_event():
    init_db()
    print("Database initialized.")

@app.get("/")
def root():
    return {"message": "EverGreen Box backend is running!"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)