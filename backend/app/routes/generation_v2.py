"""
V2 图片生成路由
提供服饰图生图的同步/异步处理接口，使用单一 Agent 提示词
"""
import os
import uuid
import aiofiles
import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Query, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.models import User, GenerationTask, TaskStatus
from app.database import get_db, SessionLocal
from app.services.image_gen_v2 import (
    process_image_with_gemini,
    preview_prompt,
    ImageGenV2Error,
    get_gemini_client
)
from app.services.prompt_template import get_agent_prompt
from app.errors import (
    AppException, ErrorCode,
    credits_insufficient_error,
    invalid_image_format_error,
    image_too_large_error,
    image_processing_failed_error,
    task_not_found_error,
    validation_error_error,
    internal_error_error
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["generation_v2"])


# ============ WebSocket 推送辅助函数 ============

async def notify_task_progress(
    user_id: int,
    task_id: int,
    status: str,
    progress: int = 0,
    result_image_url: str = None,
    elapsed_time: float = None,
    estimated_remaining: int = None,
    error_message: str = None
):
    """发送任务进度 WebSocket 通知"""
    try:
        from app.services.websocket_manager import ws_manager, TaskProgressData
        data = TaskProgressData(
            task_id=task_id,
            status=status,
            progress=progress,
            result_image_url=result_image_url,
            elapsed_time=elapsed_time,
            estimated_remaining_seconds=estimated_remaining,
            error_message=error_message
        )

        if status == "completed":
            await ws_manager.broadcast_task_complete(user_id, task_id, data)
        elif status == "failed":
            await ws_manager.broadcast_task_failed(user_id, task_id, error_message or "Unknown error")
        else:
            await ws_manager.broadcast_task_update(user_id, data)
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification: {e}")

# 配置上传目录
UPLOAD_DIR = "uploads"
RESULT_DIR = "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


def make_image_url(path: str) -> str:
    """
    将相对路径转换为完整的访问 URL

    Args:
        path: 相对路径，如 "uploads/1_original.png"

    Returns:
        完整的 URL，如 "http://localhost:8001/uploads/1_original.png"
    """
    from app.config import get_settings

    if not path:
        return ""

    # 如果已经是完整 URL，直接返回
    if path.startswith("http://") or path.startswith("https://"):
        return path

    # 从配置获取后端地址
    settings = get_settings()
    if settings.BACKEND_PORT:
        backend_url = f"http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}"
    else:
        backend_url = f"http://{settings.BACKEND_HOST}"

    # 确保路径以 / 开头
    if not path.startswith("/"):
        path = "/" + path

    return f"{backend_url}{path}"


# ============ 请求/响应模型 ============

class ProcessRequest(BaseModel):
    """图片处理请求"""
    image_path: Optional[str] = Field(None, description="图片路径（与upload_file二选一）")
    output_path: Optional[str] = Field(None, description="输出路径（可选，自动生成）")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    prompt_mode: str = Field("merge", description="提示词模式: builtin=仅内置, custom=仅自定义, merge=合并")
    timeout_seconds: int = Field(180, ge=30, le=600, description="超时时间（秒）")
    aspect_ratio: str = Field("1:1", description="宽高比")
    image_size: str = Field("1K", description="分辨率")


class ProcessUploadRequest(BaseModel):
    """图片上传处理请求"""
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    prompt_mode: str = Field("merge", description="提示词模式: builtin=仅内置, custom=仅自定义, merge=合并")
    timeout_seconds: int = Field(180, ge=30, le=600, description="超时时间（秒）")
    aspect_ratio: str = Field("1:1", description="宽高比")
    image_size: str = Field("1K", description="分辨率")


class ProcessResponse(BaseModel):
    """图片处理响应"""
    success: bool
    task_id: Optional[int] = None  # 数据库任务ID
    result_image: Optional[str] = None  # Base64 编码的图片数据
    elapsed_time: Optional[float] = None
    error_message: Optional[str] = None


class PromptPreviewResponse(BaseModel):
    """提示词预览响应"""
    prompt: str
    char_count: int


# ============ API 端点 ============

@router.post("/process", response_model=ProcessResponse)
async def process_image(
    request: ProcessRequest,
    current_user: User = Depends(get_current_user)
):
    """
    处理图片（同步接口）

    使用 Agent 提示词处理图片，生成白底图

    - 需要用户认证
    - 同步处理，直接返回结果
    """
    # 检查图片路径
    if not request.image_path:
        raise validation_error_error(
            message="需要提供 image_path 或上传图片文件",
            details={"field": "image_path"}
        )

    # 生成输出路径
    if not request.output_path:
        task_id = str(uuid.uuid4())
        ext = ".png"
        result_filename = f"{task_id}_result{ext}"
        request.output_path = os.path.join(RESULT_DIR, result_filename)

    try:
        # 执行图片处理
        result = process_image_with_gemini(
            image_path=request.image_path,
            output_path=request.output_path,
            custom_prompt=request.custom_prompt,
            timeout_seconds=request.timeout_seconds,
            aspect_ratio=request.aspect_ratio,
            image_size=request.image_size
        )

        logger.info(f"用户 {current_user.id} 图片处理成功: {request.image_path}")

        return ProcessResponse(
            success=result["success"],
            task_id=result.get("task_id"),
            elapsed_time=result["elapsed_time"],
            error_message=result.get("error_message")
        )

    except ImageGenV2Error as e:
        logger.error(f"图片处理失败: {e.message}")
        raise image_processing_failed_error(detail=e.message)
    except Exception as e:
        logger.error(f"图片处理异常: {str(e)}", exc_info=True)
        raise internal_error_error(detail=f"图片处理失败: {str(e)}")


@router.post("/process/upload", response_model=ProcessResponse)
async def process_upload(
    file: UploadFile = File(...),
    custom_prompt: Optional[str] = Form(None),
    prompt_mode: str = Form("merge"),
    timeout_seconds: int = Form(180),
    aspect_ratio: str = Form("1:1"),
    image_size: str = Form("1K"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传并处理图片（同步接口）

    上传图片后立即处理，生成白底图

    - 需要用户认证
    - 支持的最大图片大小: 10MB
    - 支持的图片格式: JPEG, PNG, WebP, TIFF
    - 支持的宽高比: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
    - 支持的分辨率: 1K, 2K, 4K
    - 自动保存任务记录到数据库
    - 生成图片名称使用任务ID
    """
    logger.info(f"收到上传请求: filename={file.filename}, content_type={file.content_type}")
    logger.info(f"生成参数: aspect_ratio={aspect_ratio}, image_size={image_size}")

    # 验证文件类型
    # 允许常见图片格式，包括浏览器可能发送的各种变体
    allowed_types = {
        'image/jpeg', 'image/jpg',
        'image/png',
        'image/webp',
        'image/tiff', 'image/tif',
        'image/heic', 'image/heif',
        'application/octet-stream'  # 某些浏览器可能发送这个
    }
    content_type = file.content_type or ''
    logger.info(f"验证文件类型: {content_type} (允许: {allowed_types})")

    # 如果不在允许列表中，尝试基于扩展名判断
    if content_type not in allowed_types:
        filename = file.filename or ''
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        image_extensions = {'jpg', 'jpeg', 'png', 'webp', 'tiff', 'tif', 'heic', 'heif'}

        if ext in image_extensions:
            logger.info(f"基于扩展名 {ext} 接受文件")
        else:
            logger.warning(f"不支持的文件类型: {content_type}, 扩展名: {ext}")
            raise invalid_image_format_error(content_type=content_type)

    # 获取文件扩展名
    ext = os.path.splitext(file.filename or '.jpg')[1] or '.jpg'

    # 检查用户积分是否足够
    if current_user.credits < 1:
        logger.warning(f"用户 {current_user.id} 积分不足: {current_user.credits}")
        raise credits_insufficient_error()

    # 扣除积分
    current_user.credits -= 1
    logger.info(f"扣除用户 {current_user.id} 积分，剩余: {current_user.credits}")

    # 创建数据库任务记录（先生成任务记录获取ID）
    db_task = GenerationTask(
        user_id=current_user.id,
        original_image_url="",
        result_image_url=None,
        status=TaskStatus.PROCESSING,
        credits_used=1,
        width=1024,
        height=1024,
        error_message=None
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    db_task_id = db_task.id

    logger.info(f"创建任务记录: task_id={db_task_id}")

    # 使用任务ID生成文件名
    original_filename = f"{db_task_id}_original{ext}"
    result_filename = f"{db_task_id}_result.png"

    original_path = os.path.join(UPLOAD_DIR, original_filename)
    result_path = os.path.join(RESULT_DIR, result_filename)

    # 更新数据库中的路径
    db_task.original_image_url = original_path
    db.commit()

    try:
        # 保存上传的文件
        logger.info(f"开始保存文件: {original_path}")
        async with aiofiles.open(original_path, "wb") as f:
            content = await file.read()
            logger.info(f"文件读取完成，大小: {len(content)} 字节")
            # 检查文件大小（最大10MB）
            if len(content) > 10 * 1024 * 1024:
                raise image_too_large_error(size_mb=len(content) / (1024 * 1024), max_mb=10)
            await f.write(content)
        logger.info(f"文件保存完成: {original_path}")

        # 执行图片处理（传递宽高比和分辨率参数）
        logger.info(f"开始调用 Gemini API...")
        logger.info(f"提示词模式: {prompt_mode}, custom_prompt: {custom_prompt[:50] if custom_prompt else '空'}...")
        result = process_image_with_gemini(
            image_path=original_path,
            output_path=result_path,
            custom_prompt=custom_prompt,
            prompt_mode=prompt_mode,
            timeout_seconds=timeout_seconds,
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )

        # 更新数据库记录
        db_task.status = TaskStatus.COMPLETED
        db.commit()

        # WebSocket 推送任务完成
        result_url = make_image_url(result_path)
        await notify_task_progress(
            user_id=current_user.id,
            task_id=db_task_id,
            status="completed",
            progress=100,
            result_image_url=result_url,
            elapsed_time=result.get("elapsed_time")
        )

        logger.info(f"用户 {current_user.id} 任务 {db_task_id} 处理成功: {original_filename}")

        return ProcessResponse(
            success=True,
            task_id=db_task_id,
            result_image=result.get("result_image"),
            elapsed_time=result.get("elapsed_time")
        )

    except AppException:
        db_task.status = TaskStatus.FAILED
        db_task.error_message = "文件验证失败"
        db.commit()
        # WebSocket 推送任务失败
        await notify_task_progress(
            user_id=current_user.id,
            task_id=db_task_id,
            status="failed",
            error_message="文件验证失败"
        )
        raise
    except ImageGenV2Error as e:
        logger.error(f"图片处理失败: {e.message}")
        db_task.status = TaskStatus.FAILED
        db_task.error_message = e.message
        db.commit()
        # WebSocket 推送任务失败
        await notify_task_progress(
            user_id=current_user.id,
            task_id=db_task_id,
            status="failed",
            error_message=e.message
        )
        raise image_processing_failed_error(detail=e.message)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"图片处理异常: {error_msg}", exc_info=True)
        db_task.status = TaskStatus.FAILED
        db_task.error_message = error_msg
        db.commit()
        # WebSocket 推送任务失败
        await notify_task_progress(
            user_id=current_user.id,
            task_id=db_task_id,
            status="failed",
            error_message=error_msg
        )
        raise internal_error_error(detail=f"处理失败: {error_msg}")


@router.get("/prompt/preview", response_model=PromptPreviewResponse)
def preview_prompt_text(
    current_user: User = Depends(get_current_user)
):
    """
    预览 Agent 提示词

    - 需要用户认证
    - 返回当前使用的 Agent 提示词
    """
    prompt = get_agent_prompt()

    return PromptPreviewResponse(
        prompt=prompt,
        char_count=len(prompt)
    )


# ============ 配置模型 ============

class GenerationConfigResponse(BaseModel):
    """生图配置响应"""
    supported_aspect_ratios: List[str]
    supported_resolutions: List[str]
    default_aspect_ratio: str
    default_resolution: str


@router.get("/config", response_model=GenerationConfigResponse)
def get_generation_config(current_user: User = Depends(get_current_user)):
    """
    获取图片生成配置

    - 需要用户认证
    - 返回支持的宽高比和分辨率列表
    """
    from app.config import get_settings
    settings = get_settings()

    return GenerationConfigResponse(
        supported_aspect_ratios=settings.SUPPORTED_ASPECT_RATIOS,
        supported_resolutions=settings.SUPPORTED_RESOLUTIONS,
        default_aspect_ratio=settings.DEFAULT_ASPECT_RATIO,
        default_resolution=settings.DEFAULT_RESOLUTION
    )


# ============ 任务历史模型 ============

class V2TaskHistoryItem(BaseModel):
    """V2任务历史项"""
    id: int
    user_id: int
    original_image_url: Optional[str] = None
    result_image_url: Optional[str] = None
    status: str
    credits_used: int
    width: int
    height: int
    created_at: str
    elapsed_time: Optional[float] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    user_action: Optional[str] = None


class V2TaskHistoryResponse(BaseModel):
    """V2任务历史响应"""
    tasks: List[V2TaskHistoryItem]
    total: int


@router.get("/tasks", response_model=V2TaskHistoryResponse)
def get_v2_task_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, pattern="^(pending|processing|completed|failed)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取V2任务历史（直接从数据库查询，不经过任务队列）

    - 支持分页
    - 支持状态过滤
    - 按创建时间降序排列
    - 实时反映任务状态
    """
    from sqlalchemy import desc

    query = db.query(GenerationTask).filter(
        GenerationTask.user_id == current_user.id
    )

    if status_filter:
        query = query.filter(GenerationTask.status == status_filter)

    tasks = query.order_by(desc(GenerationTask.created_at)).offset(skip).limit(limit).all()
    total = query.count()

    # 刷新数据库会话，确保获取最新状态
    db.expire_all()

    return V2TaskHistoryResponse(
        tasks=[
            V2TaskHistoryItem(
                id=task.id,
                user_id=task.user_id,
                original_image_url=make_image_url(task.original_image_url),
                result_image_url=make_image_url(task.result_image_url),
                status=task.status.value if hasattr(task.status, 'value') else task.status,
                credits_used=task.credits_used,
                width=task.width,
                height=task.height,
                created_at=task.created_at.isoformat() if task.created_at else "",
                elapsed_time=task.elapsed_time,
                error_message=task.error_message,
            )
            for task in tasks
        ],
        total=total
    )


@router.get("/tasks/{task_id}", response_model=V2TaskHistoryItem)
def get_v2_task_detail(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取V2任务详情（直接从数据库查询）

    - 需要用户认证
    - 只能查看自己的任务
    """
    task = db.query(GenerationTask).filter(
        GenerationTask.id == task_id,
        GenerationTask.user_id == current_user.id
    ).first()

    if not task:
        raise task_not_found_error(task_id=task_id)

    return V2TaskHistoryItem(
        id=task.id,
        user_id=task.user_id,
        original_image_url=make_image_url(task.original_image_url),
        result_image_url=make_image_url(task.result_image_url),
        status=task.status.value if hasattr(task.status, 'value') else task.status,
        credits_used=task.credits_used,
        width=task.width,
        height=task.height,
        created_at=task.created_at.isoformat() if task.created_at else "",
        error_message=task.error_message,
    )


# ============ 异步任务模型 ============

class AsyncTaskResponse(BaseModel):
    """异步任务创建响应"""
    task_id: int
    status: str
    message: str
    estimated_seconds: int = 30  # 默认预估 30 秒


class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""
    task_id: int
    status: str
    progress: int = 0  # 任务进度 0-100
    result_image_url: Optional[str] = None
    elapsed_time: Optional[float] = None
    estimated_remaining_seconds: Optional[int] = None
    error_message: Optional[str] = None


# ============ 后台任务处理 ============

async def process_task_background(
    task_id: int,
    original_path: str,
    result_path: str,
    custom_prompt: Optional[str],
    prompt_mode: str,
    timeout_seconds: int,
    aspect_ratio: str,
    image_size: str,
):
    """
    后台处理任务
    使用独立的 SessionLocal 创建会话，避免请求 Session 过期问题
    """
    db_session = None
    user_id = None
    logger.info(f"[START] [Task {task_id}] ========== 开始处理后台任务 ==========")
    logger.info(f"[PATH] [Task {task_id}] 文件路径 - 输入: {original_path}, 输出: {result_path}")
    logger.info(f"[PARAM] [Task {task_id}] 比例: {aspect_ratio}, 尺寸: {image_size}")

    async def update_progress(progress: int, estimated_remaining: int = None):
        """推送进度更新并更新数据库"""
        logger.info(f"[WS_PUSH] [Task {task_id}] 准备推送进度: {progress}%, user_id={user_id}")

        # 更新数据库progress字段
        if db_session:
            try:
                task_obj = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
                if task_obj:
                    task_obj.progress = progress
                    db_session.commit()
                    logger.info(f"[DB] [Task {task_id}] 数据库进度已更新: {progress}%")
            except Exception as db_error:
                logger.error(f"[FAILED] [Task {task_id}] 数据库进度更新失败: {db_error}")
                db_session.rollback()

        # WebSocket推送
        if user_id:
            try:
                await notify_task_progress(
                    user_id=user_id,
                    task_id=task_id,
                    status="processing",
                    progress=progress,
                    estimated_remaining=estimated_remaining
                )
                logger.info(f"[SUCCESS] [Task {task_id}] 进度推送成功: {progress}%")
            except Exception as ws_error:
                logger.error(f"[FAILED] [Task {task_id}] 进度推送失败: {ws_error}", exc_info=True)
        else:
            logger.warning(f"[WARN]  [Task {task_id}] user_id 为空，无法推送进度")

    try:
        # 创建独立的数据库 Session
        logger.info(f"[Task {task_id}] 创建 SessionLocal")
        db_session = SessionLocal()

        # 更新状态为 PROCESSING
        logger.info(f"[Task {task_id}] 查询数据库任务")
        task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if task:
            user_id = task.user_id
            logger.info(f"[Task {task_id}] 找到任务, user_id={user_id}, 状态={task.status}")
            task.status = TaskStatus.PROCESSING
            db_session.commit()
            logger.info(f"[Task {task_id}] 状态已更新为 PROCESSING")
        else:
            logger.error(f"[Task {task_id}] 未找到任务记录!")
            return

        # WebSocket 推送任务开始处理
        await update_progress(0, 30)

        logger.info(f"[PROCESS] [Task {task_id}] 后台任务开始处理")

        # 推送 30% 进度（等待一小段时间，让前端UI有时间更新）
        await asyncio.sleep(0.5)  # 500ms延迟
        await update_progress(30, 20)

        # 在线程池中执行图片处理（避免阻塞事件循环）
        logger.info(f"[API_CALL] [Task {task_id}] 开始调用 process_image_with_gemini")
        logger.info(f"[PROMPT] [Task {task_id}] 提示词模式: {prompt_mode}, custom_prompt: {custom_prompt[:50] if custom_prompt else '空'}...")
        result = await asyncio.to_thread(
            process_image_with_gemini,
            image_path=original_path,
            output_path=result_path,
            custom_prompt=custom_prompt,
            prompt_mode=prompt_mode,
            timeout_seconds=timeout_seconds,
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )
        logger.info(f"[API_DONE] [Task {task_id}] process_image_with_gemini 完成, result={result}")

        # 推送 60% 进度（添加延迟）
        await asyncio.sleep(0.3)  # 300ms延迟
        await update_progress(60, 10)

        # 推送 90% 进度（添加延迟）
        await asyncio.sleep(0.3)  # 300ms延迟
        await update_progress(90, 5)

        # 更新任务状态为 COMPLETED
        task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if task:
            task.status = TaskStatus.COMPLETED
            task.result_image_url = result_path
            task.progress = 100  # 完成时进度100%
            task.elapsed_time = result.get("elapsed_time")
            db_session.commit()

            # WebSocket 推送任务完成
            result_url = make_image_url(result_path)
            await notify_task_progress(
                user_id=user_id,
                task_id=task_id,
                status="completed",
                progress=100,
                result_image_url=result_url,
                elapsed_time=result.get("elapsed_time")
            )

        logger.info(f"后台任务完成: task_id={task_id}")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"后台任务失败: task_id={task_id}, error={error_msg}", exc_info=True)

        # 使用独立的数据库连接来更新失败状态
        db_session_for_error = None
        try:
            db_session_for_error = SessionLocal()
            task = db_session_for_error.query(GenerationTask).filter(GenerationTask.id == task_id).first()
            if task:
                user_id = task.user_id  # 确保有 user_id 用于 WebSocket 推送
                task.status = TaskStatus.FAILED
                task.error_message = error_msg

                # 退还积分（任务失败时退还）
                user = db_session_for_error.query(User).filter(User.id == user_id).first()
                if user:
                    user.credits += 1
                    logger.info(f"任务失败，退还用户 {user_id} 积分，当前积分: {user.credits}")

                db_session_for_error.commit()

                # WebSocket 推送任务失败
                if user_id:
                    await notify_task_progress(
                        user_id=user_id,
                        task_id=task_id,
                        status="failed",
                        error_message=error_msg
                    )
        except Exception as db_error:
            logger.error(f"更新失败任务状态时出错: {db_error}", exc_info=True)
        finally:
            if db_session_for_error:
                db_session_for_error.close()

    finally:
        # 关闭 Session
        if db_session:
            db_session.close()


# ============ 异步任务 API ============

@router.post("/tasks/async", response_model=AsyncTaskResponse)
async def create_async_task(
    file: UploadFile = File(...),
    custom_prompt: Optional[str] = Form(None),
    prompt_mode: str = Form("merge"),
    timeout_seconds: int = Form(180),
    aspect_ratio: str = Form("1:1"),
    image_size: str = Form("1K"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建异步任务（立即返回，后台处理）

    上传图片后立即创建任务并返回任务ID，后台异步处理生成白底图。

    - 需要用户认证
    - 支持的最大图片大小: 10MB
    - 支持的图片格式: JPEG, PNG, WebP, TIFF
    - 返回任务ID后可轮询 /api/v2/tasks/{task_id}/status 获取状态
    """
    # 验证文件类型
    allowed_types = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/tiff', 'image/tif', 'image/heic', 'image/heif'}
    content_type = file.content_type or ''

    if content_type not in allowed_types:
        filename = file.filename or ''
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        image_extensions = {'jpg', 'jpeg', 'png', 'webp', 'tiff', 'tif', 'heic', 'heif'}
        if ext not in image_extensions:
            raise invalid_image_format_error(content_type=content_type)

    # 获取文件扩展名
    ext = os.path.splitext(file.filename or '.jpg')[1] or '.jpg'

    # 检查用户积分是否足够
    if current_user.credits < 1:
        logger.warning(f"用户 {current_user.id} 积分不足: {current_user.credits}")
        raise credits_insufficient_error()

    # 扣除积分
    current_user.credits -= 1
    logger.info(f"扣除用户 {current_user.id} 积分，剩余: {current_user.credits}")

    # 创建数据库任务记录（状态为 PENDING）
    db_task = GenerationTask(
        user_id=current_user.id,
        original_image_url="",
        result_image_url=None,
        status=TaskStatus.PENDING,
        credits_used=1,
        width=1024,
        height=1024,
        error_message=None
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    task_id = db_task.id

    logger.info(f"📝 [Task {task_id}] 创建异步任务 - user_id={current_user.id}, user={current_user.username}")

    # 使用任务ID生成文件名
    original_filename = f"{task_id}_original{ext}"
    result_filename = f"{task_id}_result.png"

    original_path = os.path.join(UPLOAD_DIR, original_filename)
    result_path = os.path.join(RESULT_DIR, result_filename)

    # 更新数据库中的路径
    db_task.original_image_url = original_path
    db.commit()

    try:
        # 保存上传的文件
        async with aiofiles.open(original_path, "wb") as f:
            content = await file.read()
            if len(content) > 10 * 1024 * 1024:
                raise image_too_large_error(size_mb=len(content) / (1024 * 1024), max_mb=10)
            await f.write(content)

        # 启动后台任务
        asyncio.create_task(
            process_task_background(
                task_id=task_id,
                original_path=original_path,
                result_path=result_path,
                custom_prompt=custom_prompt,
                prompt_mode=prompt_mode,
                timeout_seconds=timeout_seconds,
                aspect_ratio=aspect_ratio,
                image_size=image_size
            )
        )

        logger.info(f"[SUCCESS] [Task {task_id}] 异步任务已启动并加入事件循环")

        return AsyncTaskResponse(
            task_id=task_id,
            status="pending",
            message="任务已创建，正在后台处理"
        )

    except AppException:
        db_task.status = TaskStatus.FAILED
        db_task.error_message = "文件验证失败"
        db.commit()
        raise
    except Exception as e:
        db_task.status = TaskStatus.FAILED
        db_task.error_message = str(e)
        db.commit()
        raise internal_error_error(detail=f"创建任务失败: {str(e)}")


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
def get_task_status(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取任务状态（轮询接口）

    - 需要用户认证
    - 只能查询自己的任务
    - 返回任务当前状态和结果（如果已完成）
    """
    from datetime import datetime, timezone

    task = db.query(GenerationTask).filter(
        GenerationTask.id == task_id,
        GenerationTask.user_id == current_user.id
    ).first()

    if not task:
        raise task_not_found_error(task_id=task_id)

    # 刷新task对象以确保获取最新的progress值
    db.refresh(task)

    # 计算预估剩余时间
    estimated_remaining = None
    if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
        # 计算已等待时间
        if task.created_at:
            created_at = task.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
            # 预估总耗时约 30 秒，剩余时间 = 30 - 已等待时间
            estimated_remaining = max(0, 30 - int(elapsed))
            # 如果等待超过 30 秒，预估为 15 秒后完成
            if estimated_remaining == 0:
                estimated_remaining = 15

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status.value if hasattr(task.status, 'value') else task.status,
        progress=task.progress if task.progress is not None else 0,  # 任务进度
        result_image_url=make_image_url(task.result_image_url) if task.result_image_url else None,
        elapsed_time=getattr(task, 'elapsed_time', None),
        estimated_remaining_seconds=estimated_remaining,
        error_message=task.error_message
    )
