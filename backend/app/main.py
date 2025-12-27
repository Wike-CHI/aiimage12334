from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(auth.router)
app.include_router(generation.router)


@app.get("/")
def root():
    return {"message": "白底图生成器 API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
