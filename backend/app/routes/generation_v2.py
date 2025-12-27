"""
V2 图片生成路由
提供服饰图生图的同步处理接口，支持提示词模板链管理
"""
import os
import uuid
import aiofiles
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.models import User
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
    template_ids: List[str] = Field(
        default=["remove_bg", "standardize", "ecommerce", "color_correct"],
        description="提示词模板ID列表"
    )
    custom_prompt: Optional[str] = Field(None, description="自定义提示词（追加到模板后）")
    timeout_seconds: int = Field(180, ge=30, le=600, description="超时时间（秒）")


class ProcessUploadRequest(BaseModel):
    """图片上传处理请求"""
    template_ids: List[str] = Field(
        default=["remove_bg", "standardize", "ecommerce", "color_correct"],
        description="提示词模板ID列表"
    )
    custom_prompt: Optional[str] = Field(None, description="自定义提示词（追加到模板后）")
    timeout_seconds: int = Field(180, ge=30, le=600, description="超时时间（秒）")


class ProcessResponse(BaseModel):
    """图片处理响应"""
    success: bool
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
            template_ids=request.template_ids,
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
    request: ProcessUploadRequest = ...,
    current_user: User = Depends(get_current_user)
):
    """
    上传并处理图片（同步接口）
    
    上传图片后立即处理，生成白底图
    
    - 需要用户认证
    - 支持的最大图片大小: 10MB
    - 支持的图片格式: JPEG, PNG, WebP, TIFF
    """
    # 验证文件类型
    allowed_types = {'image/jpeg', 'image/png', 'image/webp', 'image/tiff'}
    content_type = file.content_type or ''
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型。支持的格式: {', '.join(allowed_types)}"
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
            # 检查文件大小（最大10MB）
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="文件过大，最大支持10MB"
                )
            await f.write(content)
        
        # 执行图片处理
        result = process_image_with_gemini(
            image_path=original_path,
            output_path=result_path,
            template_ids=request.template_ids,
            custom_prompt=request.custom_prompt,
            timeout_seconds=request.timeout_seconds
        )
        
        logger.info(f"用户 {current_user.id} 上传处理成功: {original_filename}")
        
        return ProcessResponse(
            success=result["success"],
            result_path=result["result_path"],
            elapsed_time=result["elapsed_time"],
            used_templates=result["used_templates"]
        )
        
    except HTTPException:
        raise
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

