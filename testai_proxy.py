import os
import time
from openai import OpenAI
from PIL import Image
from io import BytesIO
import base64
import httpx

# 配置代理（根据你的VPN/代理服务器信息修改）
PROXY_URL = "http://127.0.0.1:7890"  # 替换为你的代理地址

# 创建支持代理的 HTTP 客户端
transport = httpx.HTTPTransport(proxy=PROXY_URL)
client = OpenAI(
    api_key="sk-yZyfgpg5rgF9JL8k818cBe9e62364213904139E91c2fD7Fa",
    base_url="http://localhost:8888/v1",
    http_client=httpx.Client(transport=transport, timeout=120.0)
)

aspect_ratio = "2:3"

prompt = (
    "Da Vinci style anatomical sketch of a dissected Monarch butterfly. "
    "Detailed drawings of the head, wings, and legs on textured parchment with notes in English."
)

print("=" * 50)
print("使用代理测试 AIHubMix Gemini API")
print(f"代理地址: {PROXY_URL}")
print("=" * 50)

start_time = time.time()

try:
    response = client.chat.completions.create(
        model="gemini-3-pro-image-preview",
        messages=[
            {"role": "system", "content": f"aspect_ratio={aspect_ratio}"},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ],
        modalities=["text", "image"]
    )
    
    api_time = time.time() - start_time
    print(f"API 调用完成，耗时: {api_time:.2f} 秒")
    print(f"响应内容: {response}")
    
    # 保存图片
    parts = response.choices[0].message.multi_mod_content
    if parts:
        for part in parts:
            if "text" in part:
                print(f"文本: {part['text']}")
            if "inline_data" in part:
                image_data = base64.b64decode(part["inline_data"]["data"])
                image = Image.open(BytesIO(image_data))
                filename = f"butterfly_{aspect_ratio.replace(':','-')}.png"
                image.save(filename)
                print(f"图片已保存: {filename} ({len(image_data)/1024:.1f} KB)")
    
    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.2f} 秒")
    
except Exception as e:
    print(f"错误: {e}")

