from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes import auth, generation
from app.database import engine, Base
from app.config import get_settings

settings = get_settings()

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="白底图生成器 API",
    description="AI 驱动的白底图生成服务",
    version="1.0.0"
)

# CORS 配置 - 支持 Tauri (8080) 和 Vite (5173) 开发服务器
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,  # http://localhost:8080
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(auth.router)
app.include_router(generation.router)

# 静态文件服务 - 上传的图片和生成结果
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/results", StaticFiles(directory="results"), name="results")


@app.get("/")
def root():
    return {"message": "白底图生成器 API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
