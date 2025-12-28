"""
V2 图片生成路由
提供服饰图生图的同步处理接口，支持提示词模板链管理
"""
import os
import uuid
import aiofiles
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.models import User, GenerationTask, TaskStatus
from app.database import get_db
from app.services.image_gen_v2 import (
    process_image_with_gemini,
    process_image_with_template_chain,
    get_available_templates,
    get_template_chains,
    preview_prompt,
    ImageGenV2Error
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["generation_v2"])

# 配置上传目录
UPLOAD_DIR = "uploads"
RESULT_DIR = "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


# ============ 请求/响应模型 ============

class ProcessRequest(BaseModel):
    """图片处理请求"""
    image_path: Optional[str] = Field(None, description="图片路径（与upload_file二选一）")
    output_path: Optional[str] = Field(None, description="输出路径（可选，自动生成）")
    template_ids: Optional[str] = Field(
        default='["remove_bg", "standardize", "ecommerce", "color_correct"]',
        description="提示词模板ID列表（JSON字符串）"
    )
    custom_prompt: Optional[str] = Field(None, description="自定义提示词（追加到模板后）")
    timeout_seconds: int = Field(180, ge=30, le=600, description="超时时间（秒）")
    
    @property
    def parsed_template_ids(self) -> List[str]:
        """解析模板ID列表"""
        if isinstance(self.template_ids, str):
            import json
            try:
                return json.loads(self.template_ids)
            except json.JSONDecodeError:
                return ["remove_bg", "standardize", "ecommerce", "color_correct"]
        return self.template_ids or ["remove_bg", "standardize", "ecommerce", "color_correct"]


class ProcessUploadRequest(BaseModel):
    """图片上传处理请求"""
    template_ids: Optional[str] = Field(
        default='["remove_bg", "standardize", "ecommerce", "color_correct"]',
        description="提示词模板ID列表（JSON字符串）"
    )
    custom_prompt: Optional[str] = Field(None, description="自定义提示词（追加到模板后）")
    timeout_seconds: int = Field(180, ge=30, le=600, description="超时时间（秒）")
    
    @property
    def parsed_template_ids(self) -> List[str]:
        """解析模板ID列表"""
        if isinstance(self.template_ids, str):
            import json
            try:
                return json.loads(self.template_ids)
            except json.JSONDecodeError:
                return ["remove_bg", "standardize", "ecommerce", "color_correct"]
        return self.template_ids or ["remove_bg", "standardize", "ecommerce", "color_correct"]


class ProcessResponse(BaseModel):
    """图片处理响应"""
    success: bool
    task_id: Optional[int] = None  # 数据库任务ID
    result_path: Optional[str] = None
    elapsed_time: Optional[float] = None
    used_templates: Optional[List[str]] = None
    error_message: Optional[str] = None


class TemplateInfo(BaseModel):
    """模板信息"""
    template_id: str
    name: str
    category: str
    description: str
    priority: int
    enabled: bool


class TemplateChainInfo(BaseModel):
    """模板链信息"""
    chain_id: str
    name: str
    template_count: int
    template_ids: List[str]


class PromptPreviewRequest(BaseModel):
    """提示词预览请求"""
    template_ids: List[str]
    product_category: str = Field("服装", description="产品类目")


class PromptPreviewResponse(BaseModel):
    """提示词预览响应"""
    prompt: str
    template_ids: List[str]
    char_count: int


# ============ API 端点 ============

@router.post("/process", response_model=ProcessResponse)
async def process_image(
    request: ProcessRequest,
    current_user: User = Depends(get_current_user)
):
    """
    处理图片（同步接口）
    
    根据指定的提示词模板链处理图片，生成白底图
    
    - 需要用户认证
    - 同步处理，直接返回结果
    - 支持自定义模板链组合
    """
    # 检查图片路径
    if not request.image_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要提供 image_path 或上传图片文件"
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
            template_ids=request.parsed_template_ids,
            custom_prompt=request.custom_prompt,
            timeout_seconds=request.timeout_seconds
        )
        
        logger.info(f"用户 {current_user.id} 图片处理成功: {request.image_path}")
        
        return ProcessResponse(
            success=result["success"],
            result_path=result["result_path"],
            elapsed_time=result["elapsed_time"],
            used_templates=result["used_templates"]
        )
        
    except ImageGenV2Error as e:
        logger.error(f"图片处理失败: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"图片处理异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理失败: {str(e)}"
        )


@router.post("/process/upload", response_model=ProcessResponse)
async def process_upload(
    file: UploadFile = File(...),
    template_ids: Optional[str] = Form('["remove_bg", "standardize", "ecommerce", "color_correct"]'),
    custom_prompt: Optional[str] = Form(None),
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
    # 解析模板ID列表
    import json
    try:
        parsed_template_ids = json.loads(template_ids) if template_ids else ["remove_bg", "standardize", "ecommerce", "color_correct"]
    except json.JSONDecodeError:
        parsed_template_ids = ["remove_bg", "standardize", "ecommerce", "color_correct"]
    
    logger.info(f"收到上传请求: filename={file.filename}, content_type={file.content_type}")
    logger.info(f"模板ID: {parsed_template_ids}")
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {content_type}。请上传 JPG、PNG、WebP 或 TIFF 格式的图片"
            )
    
    # 获取文件扩展名
    ext = os.path.splitext(file.filename or '.jpg')[1] or '.jpg'
    
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="文件过大，最大支持10MB"
                )
            await f.write(content)
        logger.info(f"文件保存完成: {original_path}")
        
        # 执行图片处理（传递宽高比和分辨率参数）
        logger.info(f"开始调用 Gemini API...")
        result = process_image_with_gemini(
            image_path=original_path,
            output_path=result_path,
            template_ids=parsed_template_ids,
            custom_prompt=custom_prompt,
            timeout_seconds=timeout_seconds,
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )
        
        # 更新数据库记录
        db_task.status = TaskStatus.COMPLETED
        db_task.result_image_url = result_path
        db.commit()
        
        logger.info(f"用户 {current_user.id} 任务 {db_task_id} 处理成功: {original_filename}")
        
        return ProcessResponse(
            success=True,
            task_id=db_task_id,
            result_path=result_path,
            elapsed_time=result.get("elapsed_time"),
            used_templates=result.get("used_templates")
        )
        
    except HTTPException:
        db_task.status = TaskStatus.FAILED
        db_task.error_message = "文件验证失败"
        db.commit()
        raise
    except ImageGenV2Error as e:
        logger.error(f"图片处理失败: {e.message}")
        db_task.status = TaskStatus.FAILED
        db_task.error_message = e.message
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"图片处理异常: {error_msg}", exc_info=True)
        db_task.status = TaskStatus.FAILED
        db_task.error_message = error_msg
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理失败: {error_msg}"
        )


@router.get("/templates", response_model=List[TemplateInfo])
def list_templates(current_user: User = Depends(get_current_user)):
    """
    获取可用的提示词模板列表
    
    - 需要用户认证
    - 返回所有已注册的模板
    """
    templates = get_available_templates()
    return templates


@router.get("/templates/{template_id}", response_model=TemplateInfo)
def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取指定模板的详细信息
    
    - 需要用户认证
    """
    from app.services.prompt_template import get_prompt_manager
    
    prompt_manager = get_prompt_manager()
    template_info = prompt_manager.get_template_info(template_id)
    
    if not template_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模板不存在: {template_id}"
        )
    
    return TemplateInfo(**template_info)


@router.get("/chains", response_model=List[TemplateChainInfo])
def list_chains(current_user: User = Depends(get_current_user)):
    """
    获取可用的模板链列表
    
    - 需要用户认证
    - 返回所有预设的模板链
    """
    chains = get_template_chains()
    return chains


@router.post("/preview", response_model=PromptPreviewResponse)
def preview_prompt_text(
    request: PromptPreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """
    预览组合后的提示词
    
    - 需要用户认证
    - 根据模板ID列表预览最终使用的提示词
    """
    prompt = preview_prompt(
        template_ids=request.template_ids,
        product_category=request.product_category
    )
    
    return PromptPreviewResponse(
        prompt=prompt,
        template_ids=request.template_ids,
        char_count=len(prompt)
    )


@router.get("/templates/categories")
def get_template_categories(current_user: User = Depends(get_current_user)):
    """
    获取模板分类列表
    
    - 需要用户认证
    - 返回所有可用的模板分类
    """
    from app.services.prompt_template import TemplateCategory
    
    return [
        {
            "category": cat.value,
            "name": cat.name.replace("_", " ")
        }
        for cat in TemplateCategory
    ]


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
                original_image_url=task.original_image_url,
                result_image_url=task.result_image_url,
                status=task.status.value if hasattr(task.status, 'value') else task.status,
                credits_used=task.credits_used,
                width=task.width,
                height=task.height,
                created_at=task.created_at.isoformat() if task.created_at else "",
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    return V2TaskHistoryItem(
        id=task.id,
        user_id=task.user_id,
        original_image_url=task.original_image_url,
        result_image_url=task.result_image_url,
        status=task.status.value if hasattr(task.status, 'value') else task.status,
        credits_used=task.credits_used,
        width=task.width,
        height=task.height,
        created_at=task.created_at.isoformat() if task.created_at else "",
    )

