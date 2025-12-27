import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import User, GenerationTask, TaskStatus
from app.schemas import GenerationTaskResponse, TaskHistoryResponse, CreditResponse
from app.auth import get_current_user
from app.services.image_gen import remove_background_with_gemini

router = APIRouter(prefix="/api", tags=["generation"])

# 配置上传目录
UPLOAD_DIR = "uploads"
RESULT_DIR = "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


@router.post("/generate", response_model=GenerationTaskResponse)
async def generate_white_bg(
    file: UploadFile = File(...),
    width: int = 1024,
    height: int = 1024,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 检查积分
    if current_user.credits < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient credits"
        )

    # 生成唯一文件名
    task_id = str(uuid.uuid4())
    original_filename = f"{task_id}_{file.filename}"
    result_filename = f"{task_id}_result.png"

    original_path = os.path.join(UPLOAD_DIR, original_filename)
    result_path = os.path.join(RESULT_DIR, result_filename)

    # 保存上传的文件
    async with aiofiles.open(original_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # 创建任务记录
    task = GenerationTask(
        user_id=current_user.id,
        original_image_url=original_path,
        result_image_url=None,
        status=TaskStatus.PROCESSING,
        credits_used=1,
        width=width,
        height=height
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        # 调用 AI 生成白底图
        await remove_background_with_gemini(original_path, result_path, width, height)

        # 更新任务状态
        task.status = TaskStatus.COMPLETED
        task.result_image_url = result_path

        # 扣除积分
        current_user.credits -= 1

        db.commit()
        db.refresh(task)

        return task

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image generation failed: {str(e)}"
        )


@router.get("/tasks", response_model=TaskHistoryResponse)
def get_task_history(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tasks = db.query(GenerationTask).filter(
        GenerationTask.user_id == current_user.id
    ).order_by(GenerationTask.created_at.desc()).offset(skip).limit(limit).all()

    total = db.query(GenerationTask).filter(
        GenerationTask.user_id == current_user.id
    ).count()

    return {"tasks": tasks, "total": total}


@router.get("/credits", response_model=CreditResponse)
def get_credits(current_user: User = Depends(get_current_user)):
    return {"credits": current_user.credits}


@router.get("/tasks/{task_id}", response_model=GenerationTaskResponse)
def get_task_detail(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(GenerationTask).filter(
        GenerationTask.id == task_id,
        GenerationTask.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task
