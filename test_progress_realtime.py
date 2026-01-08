#!/usr/bin/env python3
"""
实时进度测试 - 验证任务处理过程中的进度更新
"""
import requests
import time
import json

API_BASE = "http://129.211.218.135:8002"
TEST_IMAGE = "/www/wwwroot/生图网站/aiimage12334/34_original.png"

def main():
    print("="*70)
    print("🧪 实时进度测试")
    print("="*70)
    
    # 1. 登录
    print("\n1️⃣  登录...")
    response = requests.post(
        f"{API_BASE}/api/auth/login",
        data={"username": "226002618@nbu.edu.cn", "password": "040817lj"}
    )
    token = response.json().get("access_token")
    print(f"   ✅ 登录成功")
    
    # 2. 创建任务
    print("\n2️⃣  创建任务...")
    files = {"file": ("test.png", open(TEST_IMAGE, "rb"), "image/png")}
    data = {
        "template_ids": json.dumps(["remove_bg", "standardize"]),
        "aspect_ratio": "1:1",
        "image_size": "1024x1024",
    }
    
    response = requests.post(
        f"{API_BASE}/api/v2/tasks/async",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data
    )
    
    task_id = response.json()["task_id"]
    print(f"   ✅ 任务创建成功，ID: {task_id}")
    
    # 3. 实时监控进度
    print(f"\n3️⃣  监控进度变化（最多60秒）...")
    print("   时间  | 状态       | 进度")
    print("   " + "-"*40)
    
    seen_progress = set()
    max_attempts = 60
    
    for i in range(max_attempts):
        response = requests.get(
            f"{API_BASE}/api/v2/tasks/{task_id}/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        data = response.json()
        status = data.get("status")
        progress = data.get("progress", 0)
        
        # 只在进度变化时输出
        if progress not in seen_progress:
            seen_progress.add(progress)
            elapsed = i
            print(f"   {elapsed:3d}s | {status:10s} | {progress:3d}%")
        
        if status == "completed":
            print(f"\n   ✅ 任务完成！")
            print(f"      耗时: {data.get('elapsed_time', 0):.2f}s")
            print(f"      进度变化: {sorted(seen_progress)}")
            
            if len(seen_progress) > 1:
                print(f"\n   🎉 进度更新正常！检测到 {len(seen_progress)} 个不同进度值")
            else:
                print(f"\n   ⚠️  只检测到进度值: {seen_progress}")
            break
        elif status == "failed":
            print(f"\n   ❌ 任务失败: {data.get('error_message')}")
            break
        
        time.sleep(1)
    else:
        print(f"\n   ⏱️  超时（{max_attempts}秒）")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
