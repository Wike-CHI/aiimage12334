"""
V2 图片生成服务
基于 Gemini API 的服饰图生图功能，支持提示词模板链拼接
"""
import base64
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from PIL import Image

from app.config import get_settings
from app.services.prompt_template import (
    get_prompt_manager,
    PromptTemplateManager
)
from google import genai
from google.genai import types
from google.genai.errors import APIError

logger = logging.getLogger(__name__)
settings = get_settings()


class ImageGenV2Error(Exception):
    """V2 图片生成错误基类"""
    
    def __init__(self, message: str, code: str = "GENERATION_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class APIKeyError(ImageGenV2Error):
    """API密钥错误"""
    code = "API_KEY_ERROR"


class TimeoutExceededError(ImageGenV2Error):
    """超时错误"""
    code = "TIMEOUT_EXCEEDED"


class RateLimitError(ImageGenV2Error):
    """速率限制错误"""
    code = "RATE_LIMIT_ERROR"


class InvalidImageError(ImageGenV2Error):
    """无效图片错误"""
    code = "INVALID_IMAGE"


def validate_image(image_path: str) -> bool:
    """
    验证图片文件
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        bool: 是否有效
        
    Raises:
        InvalidImageError: 图片无效
    """
    path = Path(image_path)
    
    if not path.exists():
        raise InvalidImageError(
            f"图片文件不存在: {image_path}",
            code="FILE_NOT_FOUND"
        )
    
    if path.stat().st_size == 0:
        raise InvalidImageError(
            f"图片文件为空: {image_path}",
            code="EMPTY_FILE"
        )
    
    # 检查文件大小（最大10MB）
    max_size = 10 * 1024 * 1024
    if path.stat().st_size > max_size:
        raise InvalidImageError(
            f"图片文件过大: {path.stat().st_size} 字节 (最大 {max_size} 字节)",
            code="FILE_TOO_LARGE"
        )
    
    return True


def process_image_with_gemini(
    image_path: str,
    output_path: str,
    template_ids: Optional[List[str]] = None,
    custom_prompt: Optional[str] = None,
    timeout_seconds: int = 600,
    aspect_ratio: str = "1:1",
    image_size: str = "1K"
) -> Dict[str, Any]:
    """
    使用 Gemini API 处理图片（生成白底图）
    
    基于 test_ai.py 重构，支持提示词模板链拼接
    
    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        template_ids: 提示词模板ID列表
        custom_prompt: 自定义提示词（追加到模板后）
        timeout_seconds: 超时时间（秒）
        aspect_ratio: 宽高比，支持: "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
        image_size: 分辨率，支持: "1K", "2K", "4K"
        
    Returns:
        Dict: 包含以下键：
            - success: 是否成功
            - result_path: 输出图片路径
            - elapsed_time: 耗时（秒）
            - used_prompt: 使用的完整提示词
            - used_templates: 使用的模板ID列表
    """
    start_time = time.time()
    result = {
        "success": False,
        "result_path": None,
        "elapsed_time": 0,
        "used_prompt": "",
        "used_templates": [],
        "error_message": None
    }
    
    # 验证输入图片
    validate_image(image_path)
    
    # 读取图片
    logger.info(f"读取图片: {image_path}")
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")
    
    # 检查API密钥
    if not settings.GEMINI_API_KEY:
        raise APIKeyError(
            "GEMINI_API_KEY 未配置",
            code="MISSING_API_KEY"
        )
    
    # 获取提示词管理器
    prompt_manager = get_prompt_manager()
    
    # 构建提示词
    if template_ids is None:
        # 使用默认模板链
        template_ids = ["remove_bg", "standardize", "ecommerce", "color_correct"]
    
    # 构建完整提示词
    used_prompt = prompt_manager.build_prompt_from_chain(
        template_ids,
        product_category="服装"
    )
    
    # 追加自定义提示词
    if custom_prompt:
        used_prompt = used_prompt + "\n\n" + custom_prompt
    
    result["used_prompt"] = used_prompt
    result["used_templates"] = template_ids
    
    logger.info(f"使用模板: {template_ids}")
    logger.info(f"提示词长度: {len(used_prompt)} 字符")
    logger.info(f"生成参数: aspect_ratio={aspect_ratio}, image_size={image_size}")
    
    # 创建 Gemini 客户端（使用 AIHubMix 代理）
    logger.info(f"创建 Gemini 客户端，代理: https://aihubmix.com/gemini")
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options={"base_url": "https://aihubmix.com/gemini"},
    )
    
    logger.info(f"调用 Gemini API，模型: gemini-3-pro-image-preview")
    logger.info(f"输入图片: {image_path}")
    
    try:
        # 使用 PIL.Image 加载图片
        logger.info(f"加载图片...")
        input_image = Image.open(image_path)
        logger.info(f"图片加载完成，尺寸: {input_image.size}")
        
        # 调用 API - 图生图模式，支持宽高比和分辨率
        logger.info(f"发送 API 请求...")
        config = types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
        )
        
        # 只有文本转图片才需要 image_config，图生图模式下不需要
        # Gemini API 在图生图时会保持原图比例
        logger.info(f"等待 API 响应 (超时: {timeout_seconds}秒)...")
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[used_prompt, input_image],  # 提示词 + 图片
            config=config,
        )
        logger.info(f"API 响应接收完成")
        
        # 检查响应
        if not response or not response.parts:
            raise ImageGenV2Error(
                "Gemini API 返回空响应",
                code="EMPTY_RESPONSE"
            )
        
        # 保存生成的图片
        result_path = None
        result_image_base64 = None
        for part in response.parts:
            if part.text:
                logger.info(f"API返回文本: {part.text[:100]}...")
            elif image := part.as_image():
                # 确保输出目录存在
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                image.save(output_path)
                result_path = output_path
                logger.info(f"图片已保存: {output_path}")
                
                # 读取图片并转换为 Base64
                import base64
                with open(output_path, "rb") as img_file:
                    result_image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                logger.info(f"图片已转换为 Base64，长度: {len(result_image_base64)} 字符")
                break
        
        if not result_path:
            raise ImageGenV2Error(
                "API响应中未找到图片",
                code="NO_IMAGE_IN_RESPONSE"
            )
        
        elapsed_time = time.time() - start_time
        logger.info(f"图片处理完成，耗时: {elapsed_time:.2f}秒")
        
        result["success"] = True
        result["result_path"] = result_path
        result["result_image"] = result_image_base64
        result["elapsed_time"] = round(elapsed_time, 2)
        
        return result
        
    except APIError as e:
        error_msg = f"Gemini API 错误: {str(e)}"
        logger.error(error_msg)
        
        # 根据错误类型分类
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            raise RateLimitError(
                "API 速率限制超出，请稍后重试",
                code="RATE_LIMIT",
                details={"original_error": str(e)}
            )
        elif "DEADLINE_EXCEEDED" in str(e) or "504" in str(e):
            raise TimeoutExceededError(
                "API 请求超时",
                code="API_TIMEOUT",
                details={"original_error": str(e)}
            )
        else:
            raise ImageGenV2Error(
                error_msg,
                code="API_ERROR",
                details={"original_error": str(e)}
            )
        
    except TimeoutError as e:
        error_msg = f"请求超时: {str(e)}"
        logger.error(error_msg)
        raise TimeoutExceededError(
            error_msg,
            code="REQUEST_TIMEOUT",
            details={"original_error": str(e)}
        )
        
    except Exception as e:
        error_msg = f"图片处理时发生意外错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ImageGenV2Error(
            error_msg,
            code="UNEXPECTED_ERROR",
            details={"error_type": type(e).__name__}
        )


def process_image_with_template_chain(
    image_path: str,
    output_path: str,
    template_chain_id: str = "default",
    custom_prompt: Optional[str] = None,
    timeout_seconds: int = 600
) -> Dict[str, Any]:
    """
    使用预设模板链处理图片
    
    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        template_chain_id: 模板链ID（使用预设的链）
        custom_prompt: 自定义提示词
        timeout_seconds: 超时时间
        
    Returns:
        Dict: 处理结果
    """
    prompt_manager = get_prompt_manager()
    chain = prompt_manager.get_chain(template_chain_id)
    
    if not chain:
        raise ImageGenV2Error(
            f"模板链不存在: {template_chain_id}",
            code="CHAIN_NOT_FOUND"
        )
    
    # 构建提示词
    used_prompt = chain.build_prompt(product_category="服装")
    
    if custom_prompt:
        used_prompt = used_prompt + "\n\n" + custom_prompt
    
    # 执行处理
    return process_image_with_gemini(
        image_path=image_path,
        output_path=output_path,
        custom_prompt=custom_prompt,
        timeout_seconds=timeout_seconds
    )


def get_available_templates() -> List[Dict[str, Any]]:
    """
    获取可用的提示词模板列表
    
    Returns:
        List[Dict]: 模板信息列表
    """
    prompt_manager = get_prompt_manager()
    templates = prompt_manager.list_templates()
    
    return [
        {
            "template_id": t.template_id,
            "name": t.name,
            "category": t.category.value,
            "description": t.description,
            "priority": t.priority,
            "enabled": t.enabled
        }
        for t in templates
    ]


def get_template_chains() -> List[Dict[str, Any]]:
    """
    获取可用的模板链列表
    
    Returns:
        List[Dict]: 链信息列表
    """
    prompt_manager = get_prompt_manager()
    return prompt_manager.list_chains()


def preview_prompt(template_ids: List[str], **kwargs) -> str:
    """
    预览组合后的提示词
    
    Args:
        template_ids: 模板ID列表
        **kwargs: 变量参数
        
    Returns:
        str: 预览的提示词
    """
    prompt_manager = get_prompt_manager()
    return prompt_manager.build_prompt_from_chain(template_ids, **kwargs)

