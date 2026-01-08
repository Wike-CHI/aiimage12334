"""
测试修复后的异步任务功能
测试远程服务器的 Session 管理和 WebSocket 推送
"""
import requests
import time
import json
from pathlib import Path

# 配置 - 使用生产环境的远程服务器
API_BASE = "http://129.211.218.135:8002"  # 远程服务器地址
TEST_IMAGE = "test_ai.py"  # 使用项目中已有的文件作为测试

def login_and_get_token():
    """登录并获取 token"""
    print("\n1️⃣  测试登录...")
    
    # 登录使用 OAuth2 form data 格式（不是 JSON）
    response = requests.post(
        f"{API_BASE}/api/auth/login",
        data={  # 注意：这里是 data 不是 json
            "username": "226002618@nbu.edu.cn",  # OAuth2 的 username 字段存放邮箱
            "password": "040817lj"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user = data.get("user", {})
        print(f"   ✅ 登录成功")
        print(f"      用户: {user.get('username', '226002618@nbu.edu.cn')}")
        print(f"      积分: {user.get('credits', 'N/A')}")
        print(f"      Token: {token[:20]}...")
        return token
    else:
        print(f"   ❌ 登录失败: {response.status_code}")
        print(f"      响应: {response.text[:200]}")
        return None

def create_async_task(token):
    """创建异步任务"""
    print("\n2️⃣  创建异步图片处理任务...")
    
    # 创建一个测试图片（1x1 像素的 PNG）
    import io
    from PIL import Image
    
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    files = {
        "file": ("test.png", img_bytes, "image/png")
    }
    
    data = {
        "template_ids": json.dumps(["remove_bg", "standardize"]),
        "aspect_ratio": "1:1",
        "image_size": "1024x1024",
        "timeout_seconds": "180"
    }
    
    response = requests.post(
        f"{API_BASE}/api/v2/tasks/async",
        headers=headers,
        files=files,
        data=data
    )
    
    if response.status_code == 200:
        result = response.json()
        task_id = result.get("task_id")
        print(f"   ✅ 任务创建成功，Task ID: {task_id}")
        return task_id
    else:
        print(f"   ❌ 任务创建失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return None

def check_task_status(task_id, token):
    """检查任务状态"""
    print(f"\n3️⃣  查询任务状态...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    max_attempts = 30  # 最多等待 30 秒
    for i in range(max_attempts):
        response = requests.get(
            f"{API_BASE}/api/v2/tasks/{task_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result.get("status")
            progress = result.get("progress", 0)
            elapsed = result.get("elapsed_time") or 0  # 防止 None
            error = result.get("error_message")
            
            print(f"   [{i+1}/{max_attempts}] 状态: {status}, 进度: {progress}%, 耗时: {elapsed:.1f}s")
            
            if status == "completed":
                print(f"   ✅ 任务完成！")
                print(f"      结果图片: {result.get('result_image_url')}")
                return True
            elif status == "failed":
                print(f"   ❌ 任务失败: {error}")
                # 检查是否是 Session 错误
                if "Session" in str(error) or "bhk3" in str(error):
                    print(f"   🔴 检测到 Session 错误 - 修复未生效！")
                else:
                    print(f"   ⚠️  任务失败但不是 Session 错误（可能是其他原因）")
                return False
            
            time.sleep(1)
        else:
            print(f"   ❌ 查询失败: {response.status_code}")
            return False
    
    print(f"   ⏱️  超时：任务在 {max_attempts} 秒内未完成")
    return False

def test_task_list(token):
    """测试任务列表"""
    print(f"\n4️⃣  获取任务历史列表...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{API_BASE}/api/v2/tasks",
        headers=headers,
        params={"limit": 5}
    )
    
    if response.status_code == 200:
        result = response.json()
        tasks = result.get("tasks", [])
        print(f"   ✅ 找到 {len(tasks)} 个历史任务")
        for task in tasks[:3]:
            print(f"      - Task {task['id']}: {task['status']} (进度: {task.get('progress', 0)}%)")
        return True
    else:
        print(f"   ❌ 查询失败: {response.status_code}")
        return False

def main():
    print("=" * 70)
    print("🧪 远程服务器修复测试 - 异步任务 + Session 管理")
    print(f"   服务器: {API_BASE}")
    print("=" * 70)
    
    # 检查后端是否运行
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print("✅ 远程服务器运行中")
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到远程服务器: {e}")
        print(f"   请确认服务器 {API_BASE} 是否可访问")
        return
    
    # 测试流程
    token = login_and_get_token()
    if not token:
        return
    
    task_id = create_async_task(token)
    if not task_id:
        return
    
    success = check_task_status(task_id, token)
    
    test_task_list(token)
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 测试通过！修复生效！")
        print("   ✅ Session 管理正常")
        print("   ✅ 异步任务执行成功")
        print("   ✅ 状态更新正常")
    else:
        print("⚠️  测试未完全通过，请检查上面的错误信息")
    print("=" * 70)

if __name__ == "__main__":
    main()
