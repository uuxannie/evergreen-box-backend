from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ai  # 导入你的路由

app = FastAPI(title="EverGreen Box API")
 
# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(ai.router, prefix="/api") # 建议加个 /api 前缀

@app.get("/")
def root():
    return {"message": "EverGreen Box backend is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)