"""
FastAPI 应用主入口
白底图生成器 API 服务
"""
import time
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import WebSocket, WebSocketDisconnect, Query
from sqlalchemy import text

from app.routes import auth, generation, generation_v2
from app.database import engine, Base
from app.config import get_settings
from app.services.task_queue import task_queue
from app.services.websocket_manager import ws_manager
from app.auth import jwt
from app.errors import AppException, ErrorCode, internal_error_error

settings = get_settings()

# 记录服务启动时间
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    print(f"Database tables created")

    # 初始化任务队列
    print("Task queue initialized")
    print(f"Service started at {datetime.now().isoformat()}")

    yield

    # 关闭时执行
    print("Shutting down service...")


# 创建 FastAPI 应用
app = FastAPI(
    title="白底图生成器 API",
    description="AI 驱动的白底图生成服务，支持异步任务处理、进度追踪和错误恢复",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置 - 支持本地开发和公网访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,  # 从环境变量读取
        "http://localhost:34345",  # Tauri 开发
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Vite alternative port
        "http://127.0.0.1:34345",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://129.211.218.135:34345",  # Tauri 公网
        "http://129.211.218.135",  # 公网访问
        "http://129.211.218.135:8080",         
        "*",  # 生产环境允许所有（可根据需要调整）
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket 实时通知端点

    连接参数:
        token: JWT token (通过 query string 传递)

    连接示例:
        ws://host:8002/ws/notifications?token=your_jwt_token

    消息类型:
        - task_update: 任务进度更新
        - task_complete: 任务完成
        - task_failed: 任务失败
        - ping/pong: 心跳保活
    """
    # 验证 JWT token
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            await websocket.close(code=4001)
            return
    except Exception as e:
        print(f"WebSocket auth failed: {e}")
        await websocket.close(code=4001)
        return

    # 建立连接
    await ws_manager.connect(websocket, user_id)

    try:
        # 保持连接，接收心跳
        while True:
            data = await websocket.receive_text()
            # 心跳响应
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # 断开连接
        ws_manager.disconnect(websocket, user_id)


# 路由
app.include_router(auth.router, tags=["认证"])
app.include_router(generation.router, tags=["图片生成"])
app.include_router(generation_v2.router, tags=["图片生成V2"])

# 静态文件服务 - 上传的图片和生成结果
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/results", StaticFiles(directory="results"), name="results")


@app.get("/", summary="API 根路径")
def root():
    """API 根路径，返回服务基本信息"""
    return {
        "message": "白底图生成器 API",
        "version": "1.1.0",
        "status": "running",
        "documentation": "/docs",
        "health_check": "/health"
    }


@app.get("/health", summary="健康检查")
def health_check():
    """
    健康检查端点

    返回服务状态、版本信息和任务队列统计
    """
    # 获取任务队列统计
    queue_stats = task_queue.get_queue_stats()

    # 计算运行时间
    uptime = time.time() - start_time

    # 检查数据库连接
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "version": "1.1.0",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": round(uptime, 2),
        "database": {
            "status": db_status
        },
        "queue": {
            "total_tasks": queue_stats["total_tasks"],
            "by_status": {
                "pending": queue_stats["pending"],
                "processing": queue_stats["processing"],
                "completed": queue_stats["completed"],
                "failed": queue_stats["failed"],
                "timeout": queue_stats["timeout"],
                "cancelled": queue_stats["cancelled"]
            }
        }
    }


@app.get("/ready", summary="就绪检查")
def readiness_check():
    """
    就绪检查端点

    用于 Kubernetes 等编排系统的就绪探针
    """
    try:
        # 检查数据库连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return {"status": "ready"}

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "error": str(e)}
        )


@app.get("/metrics", summary="服务指标")
def metrics():
    """
    服务指标端点

    返回简单的服务统计信息
    """
    queue_stats = task_queue.get_queue_stats()
    uptime = time.time() - start_time

    return {
        "uptime_seconds": round(uptime, 2),
        "queue": {
            "total": queue_stats["total_tasks"],
            "active": queue_stats["pending"] + queue_stats["processing"],
            "completed": queue_stats["completed"],
            "failed": queue_stats["failed"]
        }
    }


# 异常处理
@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    """AppException 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器 - 处理未预期的异常"""
    import traceback
    import logging

    # 记录错误日志
    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())

    # 避免泄露敏感信息
    error_msg = str(exc)
    if "password" in error_msg.lower() or "secret" in error_msg.lower():
        error_msg = "Internal server error"

    return JSONResponse(
        status_code=500,
        content=internal_error_error(error_msg).to_dict()
    )
