"""
AI 图片生成服务
提供背景去除和白底图生成功能，支持异步处理和错误恢复
"""
import base64
import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path

from app.config import get_settings
from google import genai
from google.genai.errors import APIError

logger = logging.getLogger(__name__)

settings = get_settings()


class ImageGenerationError(Exception):
    """图片生成错误基类"""

    def __init__(self, message: str, code: str = "GENERATION_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class APIKeyError(ImageGenerationError):
    """API密钥错误"""
    code = "API_KEY_ERROR"


class TimeoutExceededError(ImageGenerationError):
    """超时错误"""
    code = "TIMEOUT_EXCEEDED"


class RateLimitError(ImageGenerationError):
    """速率限制错误"""
    code = "RATE_LIMIT_ERROR"


class InvalidImageError(ImageGenerationError):
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
            f"Image file not found: {image_path}",
            code="FILE_NOT_FOUND"
        )

    if path.stat().st_size == 0:
        raise InvalidImageError(
            f"Image file is empty: {image_path}",
            code="EMPTY_FILE"
        )

    # 检查文件大小 (最大 10MB)
    max_size = 10 * 1024 * 1024
    if path.stat().st_size > max_size:
        raise InvalidImageError(
            f"Image file too large: {path.stat().st_size} bytes (max {max_size} bytes)",
            code="FILE_TOO_LARGE"
        )

    return True


def remove_background_with_gemini(
    image_path: str,
    output_path: str,
    width: int = 1024,
    height: int = 1024,
    aspect_ratio: str = "1:1",
    timeout_seconds: int = 180
) -> str:
    """
    使用 AIHubMix Gemini API 去除图片背景并生成白底图

    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        width: 输出宽度
        height: 输出高度
        aspect_ratio: 宽高比
        timeout_seconds: 超时时间（秒）

    Returns:
        str: 输出图片路径

    Raises:
        APIKeyError: API密钥错误
        TimeoutExceededError: 超时错误
        RateLimitError: 速率限制错误
        ImageGenerationError: 其他生成错误
    """
    start_time = time.time()

    # 验证输入图片
    validate_image(image_path)

    # 读取图片
    logger.info(f"Reading image from {image_path}")
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")

    # 检查 API 密钥
    if not settings.GEMINI_API_KEY:
        raise APIKeyError(
            "GEMINI_API_KEY is not configured",
            code="MISSING_API_KEY"
        )

    # 创建 Gemini 客户端（使用 AIHubMix）
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options={"base_url": "https://aihubmix.com/gemini"},
    )

    # 精细化提示词
    prompt = """**第一阶段: 产品DNA精确提取**

分析输入图像中服装类目，提取并锁定以下核心细节：
- 面料材质、编织纹理、图案细节
- 精确颜色（潘通色值）
- 品牌logo或文字设计（位置、字体、大小完全一致）
- 服装各部位几何形状、尺寸比例

**第二阶段: 几何形态标准化重建**

视角要求：
- 正向对准产品中心的垂直视角
- 电商标准展示图，不改变整体比例

褶皱处理：
- 消除拍摄导致的真实不规则褶皱
- 重建为电商展示标准的平整形态
- 严格保留面料的自然纹理

结构约束：
- 服装关键结构点（纽扣位置、缝线走向、口袋形状）与原图完全一致
- 版型比例优先于褶皱消除

**第三阶段: 电商化渲染**

场景净化：
- 100%纯白背景（RGB 255,255,255），无任何阴影反光
- 移除所有非产品元素：模特、衣架、支撑物、阴影

理想化渲染：
- 均匀无影的全局光照，展示产品固有色
- 基于锁定的产品DNA，渲染清晰平整的理想化面料质感

**输出禁忌**：
- 禁止改变产品类目、材质、颜色
- 禁止添加任何装饰元素
- 禁止添加标签、洗水标、尺码标、吊牌
- 禁止出现阴影、反光、渐变背景
- 禁止改变缝合线走向
- 禁止调整纽扣/口袋/扣眼的数量和位置

只输出处理后的图片，不要任何文字说明。"""

    logger.info(f"Calling Gemini API with model gemini-3-pro-image-preview")

    try:
        # 调用 API
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[
                prompt,
                {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
            ],
        )

        # 检查响应
        if not response or not response.parts:
            raise ImageGenerationError(
                "Empty response from Gemini API",
                code="EMPTY_RESPONSE"
            )

        # 保存生成的图片
        result_path = None
        for part in response.parts:
            if image := part.as_image():
                # 确保输出目录存在
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)

                image.save(output_path)
                result_path = output_path
                break

        if not result_path:
            raise ImageGenerationError(
                "No image in API response",
                code="NO_IMAGE_IN_RESPONSE"
            )

        elapsed_time = time.time() - start_time
        logger.info(f"Image generation completed in {elapsed_time:.2f}s")

        return result_path

    except APIError as e:
        error_msg = f"Gemini API error: {str(e)}"
        logger.error(error_msg)

        # 根据错误类型分类
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            raise RateLimitError(
                "API rate limit exceeded. Please try again later.",
                code="RATE_LIMIT",
                details={"original_error": str(e)}
            )
        elif "DEADLINE_EXCEEDED" in str(e) or "504" in str(e):
            raise TimeoutExceededError(
                "API request timed out",
                code="API_TIMEOUT",
                details={"original_error": str(e)}
            )
        else:
            raise ImageGenerationError(
                error_msg,
                code="API_ERROR",
                details={"original_error": str(e)}
            )

    except TimeoutError as e:
        error_msg = f"Request timeout: {str(e)}"
        logger.error(error_msg)
        raise TimeoutExceededError(
            error_msg,
            code="REQUEST_TIMEOUT",
            details={"original_error": str(e)}
        )

    except Exception as e:
        error_msg = f"Unexpected error during image generation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ImageGenerationError(
            error_msg,
            code="UNEXPECTED_ERROR",
            details={"error_type": type(e).__name__}
        )


def remove_background_with_gemini_async(
    image_path: str,
    output_path: str,
    width: int = 1024,
    height: int = 1024,
    aspect_ratio: str = "1:1",
    timeout_seconds: int = 180
) -> str:
    """
    异步版本的图片处理函数（实际上是同步调用，由任务队列在后台线程执行）
    """
    return remove_background_with_gemini(
        image_path=image_path,
        output_path=output_path,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        timeout_seconds=timeout_seconds
    )


def generate_white_bg_with_retry(
    image_path: str,
    output_path: str,
    width: int = 1024,
    height: int = 1024,
    aspect_ratio: str = "1:1",
    max_retries: int = 2,
    timeout_seconds: int = 180
) -> str:
    """
    带重试机制的图片生成

    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        width: 输出宽度
        height: 输出高度
        aspect_ratio: 宽高比
        max_retries: 最大重试次数
        timeout_seconds: 超时时间

    Returns:
        str: 输出图片路径

    Raises:
        ImageGenerationError: 重试后仍然失败
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Image generation attempt {attempt + 1}/{max_retries + 1}")

            return remove_background_with_gemini(
                image_path=image_path,
                output_path=output_path,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                timeout_seconds=timeout_seconds
            )

        except (RateLimitError, TimeoutExceededError) as e:
            # 这些错误可以重试
            last_error = e
            wait_time = (attempt + 1) * 5  # 递增等待时间
            logger.warning(f"Retryable error, waiting {wait_time}s before retry: {e}")
            time.sleep(wait_time)

        except APIKeyError:
            # API密钥错误，重试也无法解决
            raise

        except ImageGenerationError as e:
            if e.code in ["INVALID_IMAGE", "API_KEY_ERROR", "QUOTA_EXCEEDED"]:
                # 这些错误不应该重试
                raise
            last_error = e

        except Exception as e:
            last_error = e

    # 所有重试都失败了
    if last_error:
        raise ImageGenerationError(
            f"Image generation failed after {max_retries + 1} attempts: {str(last_error)}",
            code="MAX_RETRIES_EXCEEDED",
            details={"last_error": str(last_error)}
        )

    raise ImageGenerationError("Image generation failed", code="UNKNOWN_ERROR")
