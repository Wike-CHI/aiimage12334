import os
import time
from openai import OpenAI
from PIL import Image
from io import BytesIO
import base64

# 创建客户端（使用 OpenAI 兼容格式）
client = OpenAI(
    api_key="sk-yZyfgpg5rgF9JL8k818cBe9e62364213904139E91c2fD7Fa",
    base_url="http://localhost:8888/v1",
)

# 可选参数
aspect_ratio = "1:1"

prompt = (
    "big boobs girl, naked, in bed, looking at the camera, sexy, "
)

print("=" * 50)
print("开始测试 AIHubMix Gemini API")
print("=" * 50)

# 第1步：测量 API 调用时间
print("\n[步骤1] 调用 API...")
start_time = time.time()
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

# 第2步：测量图片保存时间
print("\n[步骤2] 处理并保存图片...")
save_start = time.time()

try:
    parts = response.choices[0].message.multi_mod_content
    if parts:
        for part in parts:
            if "text" in part:
                print(f"文本内容: {part['text']}")
            if "inline_data" in part:
                print(f"检测到图片数据...")
                image_data = base64.b64decode(part["inline_data"]["data"])
                print(f"图片数据大小: {len(image_data) / 1024:.2f} KB")
                
                save_start_img = time.time()
                image = Image.open(BytesIO(image_data))
                print(f"Image.open() 耗时: {time.time() - save_start_img:.2f} 秒")
                
                filename = f"butterfly_{aspect_ratio.replace(':','-')}.png"
                
                save_start_write = time.time()
                image.save(filename)
                write_time = time.time() - save_start_write
                
                print(f"image.save() 耗时: {write_time:.2f} 秒")
                print(f"Image saved: {filename}")
    else:
        print("No valid multimodal response received.")
        
except Exception as e:
    print(f"Error: {str(e)}")

total_time = time.time() - start_time
print("\n" + "=" * 50)
print(f"总耗时: {total_time:.2f} 秒")
print("=" * 50)

