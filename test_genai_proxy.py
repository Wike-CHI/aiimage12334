import os
import sys
import time
sys.path.insert(0, '/www/wwwroot/生图网站/aiimage12334/backend')

from google import genai
from google.genai import types

# 从配置文件读取 API Key
with open("/www/wwwroot/生图网站/aiimage12334/backend/.env", "r") as file:
    for line in file:
        if "GEMINI_API_KEY" in line:
            API_KEY = line.split("=")[1].strip()
            break

print("=" * 50)
print("测试 Genai 客户端通过反向代理")
print("=" * 50)
print(f"API Key: {API_KEY[:10]}...")
print(f"代理地址: http://localhost:8888/gemini")
print()

# 创建客户端（通过本地代理）
client = genai.Client(
    api_key=API_KEY,
    http_options={"base_url": "http://localhost:8888/gemini"},
)

print("客户端创建成功")
print()

# 测试简单请求
print("[测试1] 简单文本生成...")
start = time.time()

try:
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents="Hello, this is a test.",
    )
    
    elapsed = time.time() - start
    print(f"✓ 成功! 耗时: {elapsed:.2f}秒")
    print(f"响应: {response.text[:100] if response.text else 'No text'}")
    
except Exception as e:
    elapsed = time.time() - start
    print(f"✗ 失败! 耗时: {elapsed:.2f}秒")
    print(f"错误: {e}")

print()
print("=" * 50)

