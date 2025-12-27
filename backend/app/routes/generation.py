"""
图片生成路由
支持任务提交、状态查询、进度追踪和结果获取
"""
import os
import uuid
import asyncio
import aiofiles
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import User, GenerationTask, TaskStatus as DBTaskStatus
from app.schemas import (
    TaskHistoryResponse,
    CreditResponse,
    TaskStatusResponse,
    TaskSubmitResponse,
    APIResponse
)
from app.auth import get_current_user
from app.services.image_gen import remove_background_with_gemini_async, ImageGenerationError
from app.services.task_queue import task_queue, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generation"])

# 配置上传目录
UPLOAD_DIR = "uploads"
RESULT_DIR = "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


def convert_db_status(db_status: DBTaskStatus) -> TaskStatus:
    """将数据库任务状态转换为队列任务状态"""
    status_mapping = {
        DBTaskStatus.PENDING: TaskStatus.PENDING,
        DBTaskStatus.PROCESSING: TaskStatus.PROCESSING,
        DBTaskStatus.COMPLETED: TaskStatus.COMPLETED,
        DBTaskStatus.FAILED: TaskStatus.FAILED,
    }
    return status_mapping.get(db_status, TaskStatus.PENDING)


def _resubmit_task_internal(
    task_id: int,
    deduct_credits: bool,
    width: int,
    height: int,
    ratio: str,
    current_user: User,
    db: Session
) -> TaskSubmitResponse:
    """
    重新提交任务的内部实现

    Args:
        task_id: 原任务ID
        deduct_credits: 是否扣除积分
        width: 输出宽度
        height: 输出高度
        ratio: 宽高比
        current_user: 当前用户
        db: 数据库会话

    Returns:
        TaskSubmitResponse: 提交响应
    """
    # 获取原任务
    original_task = db.query(GenerationTask).filter(
        GenerationTask.id == task_id,
        GenerationTask.user_id == current_user.id
    ).first()

    if not original_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # 检查是否可以重新提交
    if original_task.status == DBTaskStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is still processing"
        )

    # 检查任务状态是否允许重新提交
    allowed_statuses = [DBTaskStatus.FAILED, DBTaskStatus.CANCELLED]
    if original_task.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task cannot be resubmitted. Only failed or cancelled tasks can be resubmitted."
        )

    # 扣积分逻辑
    if deduct_credits:
        if current_user.credits < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient credits"
            )
        current_user.credits -= 1

    # 生成新的任务ID
    new_task_id = str(uuid.uuid4())
    result_filename = f"{new_task_id}_result.png"

    # 使用原图
    original_path = original_task.original_image_url
    result_path = os.path.join(RESULT_DIR, result_filename)

    # 创建新任务记录
    new_task = GenerationTask(
        user_id=current_user.id,
        original_image_url=original_path,
        result_image_url=None,
        status=DBTaskStatus.PENDING,
        credits_used=1 if deduct_credits else 0,
        width=width,
        height=height,
        error_message=None
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # 提交到任务队列
    task_queue.submit_task(
        user_id=current_user.id,
        task_func=remove_background_with_gemini_async,
        args=(original_path, result_path, width, height, ratio),
        kwargs={"timeout_seconds": 180},
        timeout_seconds=200
    )

    # 更新新任务状态
    new_task.status = DBTaskStatus.PROCESSING
    db.commit()

    logger.info(f"Resubmit task {new_task_id} created from original task {task_id}")

    return TaskSubmitResponse(
        task_id=new_task_id,
        status=TaskStatus.PROCESSING.value,
        message="Task resubmitted successfully",
        estimated_time=60,
        db_task_id=new_task.id
    )


def convert_queue_status(queue_status: TaskStatus) -> DBTaskStatus:
    """将队列任务状态转换为数据库任务状态"""
    status_mapping = {
        TaskStatus.PENDING: DBTaskStatus.PENDING,
        TaskStatus.PROCESSING: DBTaskStatus.PROCESSING,
        TaskStatus.COMPLETED: DBTaskStatus.COMPLETED,
        TaskStatus.FAILED: DBTaskStatus.FAILED,
        TaskStatus.TIMEOUT: DBTaskStatus.FAILED,
        TaskStatus.CANCELLED: DBTaskStatus.FAILED,
    }
    return status_mapping.get(queue_status, DBTaskStatus.PENDING)


@router.post("/generate", response_model=TaskSubmitResponse)
async def generate_white_bg(
    file: UploadFile = File(...),
    width: int = Query(1024, ge=100, le=4096),
    height: int = Query(1024, ge=100, le=4096),
    ratio: str = Query("1:1"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    提交白底图生成任务

    - 异步处理，无需等待生成完成
    - 通过返回的 task_id 轮询任务状态
    - 支持的最大图片大小: 10MB
    - 默认超时时间: 3分钟
    """
    # 检查积分
    if current_user.credits < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient credits"
        )

    # 验证文件类型
    allowed_types = {'image/jpeg', 'image/png', 'image/webp', 'image/tiff'}
    content_type = file.content_type or ''
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # 生成唯一文件名
    task_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or '.jpg')[1] or '.jpg'
    original_filename = f"{task_id}_{current_user.id}{ext}"
    result_filename = f"{task_id}_result.png"

    original_path = os.path.join(UPLOAD_DIR, original_filename)
    result_path = os.path.join(RESULT_DIR, result_filename)

    try:
        # 保存上传的文件
        async with aiofiles.open(original_path, "wb") as f:
            content = await file.read()
            # 检查文件大小 (最大 10MB)
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File too large. Maximum size is 10MB"
                )
            await f.write(content)

        # 创建数据库任务记录
        db_task = GenerationTask(
            user_id=current_user.id,
            original_image_url=original_path,
            result_image_url=None,
            status=DBTaskStatus.PENDING,
            credits_used=1,
            width=width,
            height=height,
            error_message=None
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)

        # 提交到任务队列
        queue_task = task_queue.submit_task(
            user_id=current_user.id,
            task_func=remove_background_with_gemini_async,
            args=(original_path, result_path, width, height, ratio),
            kwargs={"timeout_seconds": 180},
            timeout_seconds=200  # 额外缓冲时间
        )

        # 更新数据库任务状态
        db_task.status = DBTaskStatus.PROCESSING
        db.commit()

        logger.info(f"Task {task_id} submitted for user {current_user.id}")

        return TaskSubmitResponse(
            task_id=task_id,
            status=TaskStatus.PROCESSING.value,
            message="Task submitted successfully. Please poll the status endpoint to check progress.",
            estimated_time=60,  # 预计60秒
            db_task_id=db_task.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}"
        )


@router.get("/tasks", response_model=TaskHistoryResponse)
def get_task_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, pattern="^(pending|processing|completed|failed)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户任务历史

    - 支持分页
    - 支持状态过滤
    - 按创建时间降序排列
    """
    query = db.query(GenerationTask).filter(
        GenerationTask.user_id == current_user.id
    )

    if status_filter:
        query = query.filter(GenerationTask.status == DBTaskStatus(status_filter))

    tasks = query.order_by(desc(GenerationTask.created_at)).offset(skip).limit(limit).all()
    total = query.count()

    # 同步队列中的最新状态
    for task in tasks:
        queue_task = task_queue.get_task(str(task.id))
        if queue_task and queue_task.status != convert_db_status(task.status):
            # 更新数据库中的状态
            task.status = convert_queue_status(queue_task.status)
            if queue_task.status == TaskStatus.COMPLETED:
                task.result_image_url = queue_task.result
            elif queue_task.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT]:
                task.error_message = queue_task.error_message or "Task failed"

    db.commit()

    return {"tasks": tasks, "total": total}


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取单个任务状态

    - 包含详细的状态信息
    - 包含进度百分比（如果可用）
    - 包含错误信息（如果失败）
    """
    task = db.query(GenerationTask).filter(
        GenerationTask.id == task_id,
        GenerationTask.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # 检查队列中的最新状态
    queue_task = task_queue.get_task(str(task_id))

    response_data = {
        "id": task.id,
        "status": task.status.value if isinstance(task.status, DBTaskStatus) else task.status,
        "progress": 0,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "original_image_url": task.original_image_url,
        "result_image_url": task.result_image_url,
        "error_message": task.error_message,
        "width": task.width,
        "height": task.height,
        "credits_used": task.credits_used,
        "is_timed_out": False,
        "can_retry": False
    }

    if queue_task:
        # 更新进度和状态
        response_data["progress"] = queue_task.progress
        response_data["is_timed_out"] = queue_task.is_timed_out()

        # 如果队列状态与数据库不同步，更新数据库
        db_status = convert_db_status(task.status)
        if queue_task.status != db_status:
            task.status = convert_queue_status(queue_task.status)
            if queue_task.status == TaskStatus.COMPLETED:
                task.result_image_url = queue_task.result
            elif queue_task.status == TaskStatus.FAILED:
                task.error_message = queue_task.error_message
            db.commit()
            response_data["status"] = queue_task.status.value

        # 判断是否允许重试
        if queue_task.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT]:
            response_data["can_retry"] = True
            response_data["error_message"] = queue_task.error_message

    return response_data


@router.post("/tasks/{task_id}/retry", response_model=TaskSubmitResponse)
def retry_task(
    task_id: int,
    width: int = Query(1024, ge=100, le=4096),
    height: int = Query(1024, ge=100, le=4096),
    ratio: str = Query("1:1"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    重试失败的任务

    - 只能重试失败或超时的任务
    - 不会扣除积分
    """
    # 调用内部实现，不扣积分
    return _resubmit_task_internal(
        task_id=task_id,
        deduct_credits=False,  # 重试不扣积分
        width=width,
        height=height,
        ratio=ratio,
        current_user=current_user,
        db=db
    )


@router.delete("/tasks/{task_id}/delete")
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除任务（从历史记录中移除）

    - 只能删除已完成、失败或取消的任务
    - 删除后任务将不再显示在历史记录中
    """
    task = db.query(GenerationTask).filter(
        GenerationTask.id == task_id,
        GenerationTask.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # 只能删除非活跃状态的任务
    if task.status in [DBTaskStatus.PENDING, DBTaskStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active tasks. Please cancel first."
        )

    # 从数据库删除
    db.delete(task)
    db.commit()

    # 如果队列中有对应任务，也移除
    queue_task = task_queue.get_task(str(task_id))
    if queue_task:
        del task_queue._tasks[str(task_id)]

    return {"message": "Task deleted successfully"}


@router.post("/tasks/{task_id}/continue", response_model=TaskSubmitResponse)
def continue_task(
    task_id: int,
    width: int = Query(1024, ge=100, le=4096),
    height: int = Query(1024, ge=100, le=4096),
    ratio: str = Query("1:1"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    继续生成失败或被取消的任务

    - 使用原图重新提交到任务队列
    - 失败的任务会扣除积分重新生成
    - 被取消的任务不会再次扣除积分
    """
    # 获取原任务以确定是否扣积分
    original_task = db.query(GenerationTask).filter(
        GenerationTask.id == task_id,
        GenerationTask.user_id == current_user.id
    ).first()

    if not original_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # 失败的任务扣积分，取消的任务不扣积分
    deduct_credits = original_task.status == DBTaskStatus.FAILED

    # 调用内部实现
    return _resubmit_task_internal(
        task_id=task_id,
        deduct_credits=deduct_credits,
        width=width,
        height=height,
        ratio=ratio,
        current_user=current_user,
        db=db
    )


@router.post("/tasks/{task_id}/resubmit", response_model=TaskSubmitResponse)
def resubmit_task(
    task_id: int,
    deduct_credits: bool = Query(True, description="是否扣除积分，true=扣积分，false=不扣积分"),
    width: int = Query(1024, ge=100, le=4096),
    height: int = Query(1024, ge=100, le=4096),
    ratio: str = Query("1:1"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    重新提交任务（统一接口）

    - 可用于重试失败/超时的任务，或继续被取消的任务
    - 通过 deduct_credits 参数控制是否扣除积分
    - 推荐使用此接口，retry 和 continue 作为快捷方式保留
    """
    return _resubmit_task_internal(
        task_id=task_id,
        deduct_credits=deduct_credits,
        width=width,
        height=height,
        ratio=ratio,
        current_user=current_user,
        db=db
    )


@router.delete("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    取消正在处理的任务（立即中止）
    """
    task = db.query(GenerationTask).filter(
        GenerationTask.id == task_id,
        GenerationTask.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    if task.status not in [DBTaskStatus.PENDING, DBTaskStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task cannot be cancelled. Only pending or processing tasks can be cancelled."
        )

    # 取消队列中的任务
    queue_task = task_queue.get_task(str(task_id))
    if queue_task:
        task_queue.cancel_task(str(task_id))

    # 更新数据库状态
    task.status = DBTaskStatus.FAILED
    task.error_message = "Task cancelled by user"
    db.commit()

    return {"message": "Task cancelled successfully"}


@router.get("/credits", response_model=CreditResponse)
def get_credits(current_user: User = Depends(get_current_user)):
    """获取用户积分"""
    return {"credits": current_user.credits}


@router.get("/queue/stats")
def get_queue_stats(current_user: User = Depends(get_current_user)):
    """获取队列统计信息（仅管理员可用，此处简化）"""
    stats = task_queue.get_queue_stats()
    return stats
