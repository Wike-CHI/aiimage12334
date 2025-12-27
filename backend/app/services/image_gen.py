import base64
from app.config import get_settings
from google import genai
from google.genai import types

settings = get_settings()


def remove_background_with_gemini(image_path: str, output_path: str, width: int, height: int, aspect_ratio: str = "1:1") -> str:
    """
    使用 AIHubMix Gemini API 去除图片背景并生成白底图
    """
    # 读取图片
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")

    # 创建 Gemini 客户端（使用 AIHubMix）
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options={"base_url": "https://aihubmix.com/gemini"},
    )

    # 根据分辨率设置 image_size (根据最大边计算)
    max_pixels = max(width, height)
    if max_pixels <= 1024:
        image_size = "1K"
    elif max_pixels <= 2048:
        image_size = "2K"
    else:
        image_size = "4K"

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

    # 调用 API
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[prompt, {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            ),
        ),
    )

    # 保存生成的图片
    for part in response.parts:
        if image := part.as_image():
            image.save(output_path)
            return output_path

    raise Exception("Failed to generate image")


def remove_background_with_gemini_async(image_path: str, output_path: str, width: int, height: int, aspect_ratio: str = "1:1") -> str:
    """
    同步版本的图片处理函数
    """
    return remove_background_with_gemini(image_path, output_path, width, height, aspect_ratio)
