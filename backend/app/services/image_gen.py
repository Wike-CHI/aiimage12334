import base64
import httpx
import json
from app.config import get_settings

settings = get_settings()


async def remove_background_with_gemini(image_path: str, output_path: str, width: int, height: int) -> str:
    """
    使用 Gemini API 去除图片背景
    """
    # 读取图片并进行 base64 编码
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")

    # Gemini API 请求
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"

    prompt = f"""请帮我处理这张图片，做成白底商品图。要求：
1. 去除图片背景
2. 将背景设置为纯白色 (#FFFFFF)
3. 保持商品主体的完整性和清晰度
4. 图片尺寸调整为 {width} x {height} 像素
5. 直接返回处理后的图片，不需要解释

请以 base64 格式返回处理后的图片，只返回图片数据，不需要任何文字说明。"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=payload, timeout=120.0)
        response.raise_for_status()

        result = response.json()
        # 解析 Gemini 返回的 base64 图片
        generated_content = result["candidates"][0]["content"]["parts"][0]["text"]

        # 去除可能的 markdown 格式
        if "```json" in generated_content:
            generated_content = generated_content.split("```json")[1].split("```")[0]
        elif "```" in generated_content:
            generated_content = generated_content.split("```")[1].split("```")[0]

        image_data = json.loads(generated_content).get("image", {}).get("data")

        if image_data:
            # 保存处理后的图片
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            return output_path
        else:
            raise Exception("Failed to generate image")
