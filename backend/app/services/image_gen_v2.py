"""
V2 图片生成服务
基于 Gemini API 的服饰图生图功能，使用单一 Agent 提示词
"""
import base64
import io
import logging
import time
from pathlib import Path
from typing import Optional, Dict

from PIL import Image, ImageOps

from app.config import get_settings
from app.services.prompt_template import get_agent_prompt
from google import genai
from google.genai import types
from google.genai.errors import APIError

logger = logging.getLogger(__name__)
settings = get_settings()

# Gemini 客户端缓存
_gemini_client = None


def get_gemini_client():
    """
    获取 Gemini 客户端（单例模式）

    Returns:
        genai.Client: Gemini API 客户端
    """
    global _gemini_client

    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options={"base_url": "https://aihubmix.com/gemini"},
        )
        logger.info("Gemini 客户端初始化完成")

    return _gemini_client


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


def whiten_background(image: Image.Image) -> Image.Image:
    """
    将图片背景强制转换为纯白色

    遍历所有像素，将接近白色的浅色背景强制设为纯白 RGB(255,255,255)
    保留衣服本身的颜色不受影响。

    Args:
        image: PIL Image 对象

    Returns:
        处理后的 Image 对象
    """
    # 转换为RGB模式
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # 获取图片数据
    pixels = image.load()
    width, height = image.size

    # 遍历所有像素
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y]
            # 判断是否为背景区域（浅色像素）
            # 条件：R、G、B 都大于阈值，且整体偏白
            if r > 240 and g > 240 and b > 240:
                # 检查是否可能是衣服上的白色区域（避免误伤）
                # 如果 R、G、B 差异很小，说明是中性色，很可能是背景
                color_diff = max(r, g, b) - min(r, g, b)
                if color_diff < 50:  # 中性色容差
                    pixels[x, y] = (255, 255, 255)

    return image


def calculate_target_size(aspect_ratio: str, image_size: str) -> tuple[int, int]:
    """
    计算目标图片尺寸
    
    Args:
        aspect_ratio: 宽高比 (e.g., "16:9")
        image_size: 分辨率档位 ("1K", "2K", "4K")
        
    Returns:
        tuple[int, int]: (width, height)
    """
    # 基准长边尺寸
    size_map = {
        "1K": 1024,
        "2K": 2048,
        "4K": 4096
    }
    base_size = size_map.get(image_size, 1024)

    try:
        w_ratio, h_ratio = map(int, aspect_ratio.split(":"))
    except ValueError:
        w_ratio, h_ratio = 1, 1

    if w_ratio > h_ratio:
        # 横向：宽度为基准，高度按比例计算
        width = base_size
        height = int(base_size * (h_ratio / w_ratio))
    else:
        # 纵向或正方：高度为基准，宽度按比例计算
        height = base_size
        width = int(base_size * (w_ratio / h_ratio))

    return width, height


def process_image_with_gemini(
    image_path: str,
    output_path: str,
    custom_prompt: Optional[str] = None,
    timeout_seconds: int = 600,
    aspect_ratio: str = "1:1",
    image_size: str = "1K"
) -> Dict[str, Any]:
    """
    使用 Gemini API 处理图片（生成白底图）
    使用单一 Agent 提示词

    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        custom_prompt: 自定义提示词（追加到 Agent 提示词后）
        timeout_seconds: 超时时间（秒）
        aspect_ratio: 宽高比，支持: "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
        image_size: 分辨率，支持: "1K", "2K", "4K"

    Returns:
        Dict: 包含以下键：
            - success: 是否成功
            - result_path: 输出图片路径
            - elapsed_time: 耗时（秒）
            - used_prompt: 使用的完整提示词
    """
    start_time = time.time()
    result = {
        "success": False,
        "result_path": None,
        "elapsed_time": 0,
        "used_prompt": "",
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

    # 获取 Agent 提示词
    used_prompt = get_agent_prompt()

    # 追加自定义提示词
    if custom_prompt:
        used_prompt = used_prompt + "\n\n" + custom_prompt

    result["used_prompt"] = used_prompt

    logger.info(f"使用 Agent 提示词")
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
            elif gemini_image := part.as_image():
                # types.Image 有 image_bytes 字段，包含图片数据
                image_bytes = gemini_image.image_bytes
                image = Image.open(io.BytesIO(image_bytes))

                # 自动修正 EXIF 方向（旋转90度等问题）
                image = ImageOps.exif_transpose(image)
                logger.info(f"Gemini返回图片尺寸（修正EXIF后）: {image.size}")

                # 确保输出目录存在
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)

                # 计算目标尺寸并调整
                target_width, target_height = calculate_target_size(aspect_ratio, image_size)
                logger.info(f"目标尺寸: {target_width}x{target_height}")
                logger.info(f"当前图片尺寸: {image.size}")

                # 记录比例用于调试
                image_ratio = image.width / image.height if image.height > 0 else 1
                target_ratio = target_width / target_height if target_height > 0 else 1
                logger.info(f"图片比例: {image_ratio:.2f}, 目标比例: {target_ratio:.2f}")

                # 检测 Gemini 是否返回了旋转的图片
                # 对于 1:1 输出，只有当图片明显是横图(宽是高1.5倍以上)时才旋转
                if target_ratio == 1 and image.width > image.height and image.width / image.height > 1.5:
                    image = image.rotate(-90, expand=True)
                    logger.warning(f"检测到横图，旋转校正为竖图，新尺寸: {image.size}")
                else:
                    logger.info(f"图片方向正确，无需旋转")

                if image.size != (target_width, target_height):
                    # 使用 contain 保持比例，用白边填充，避免裁剪
                    logger.info(f"调整图片尺寸: {image.size} -> ({target_width}, {target_height}) (使用等比缩放+白边填充)")
                    scaled_image = ImageOps.contain(image, (target_width, target_height), Image.Resampling.LANCZOS)
                    # 创建白底画布并粘贴缩放后的图片（居中）
                    image = Image.new('RGB', (target_width, target_height), 'white')
                    paste_x = (target_width - scaled_image.width) // 2
                    paste_y = (target_height - scaled_image.height) // 2
                    image.paste(scaled_image, (paste_x, paste_y))
                    logger.info(f"已添加白边填充，图片尺寸: {image.size}")
                else:
                    logger.info(f"图片尺寸已符合目标尺寸，无需调整")

                # Gemini 已直接生成纯白背景，无需额外 whiten_background 处理
                logger.info(f"跳过 whiten_background，保留 Gemini 原生输出")

                image.save(output_path)
                result_path = output_path
                logger.info(f"图片已保存: {output_path}")
                
                # 读取图片并转换为 Base64
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


def preview_prompt() -> str:
    """
    预览 Agent 提示词

    Returns:
        str: Agent 提示词内容
    """
    return get_agent_prompt()
