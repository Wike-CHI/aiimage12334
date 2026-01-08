"""
测试修复后的异步任务处理
验证 Session 生命周期是否正确
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import SessionLocal, get_db
from app.models import GenerationTask, TaskStatus

def test_session_lifecycle():
    """测试 Session 生命周期"""
    print("测试 1: 创建独立 Session")
    
    # 模拟异步任务中的 Session 创建
    db_session = next(get_db())
    print(f"  ✓ Session 创建成功: {db_session}")
    
    try:
        # 模拟查询操作
        tasks = db_session.query(GenerationTask).limit(5).all()
        print(f"  ✓ 查询成功，找到 {len(tasks)} 个任务")
        
        # 模拟更新操作
        if tasks:
            task = tasks[0]
            print(f"  ✓ 任务 ID: {task.id}, 状态: {task.status}")
    except Exception as e:
        print(f"  ✗ 错误: {e}")
    finally:
        db_session.close()
        print("  ✓ Session 已关闭")
    
    print("\n测试 2: 验证 Session 关闭后不可用")
    try:
        # 尝试在关闭后使用 Session
        db_session.query(GenerationTask).first()
        print("  ✗ 错误：Session 关闭后仍可使用（不应该发生）")
    except Exception as e:
        print(f"  ✓ 正确：Session 关闭后不可用 ({type(e).__name__})")

if __name__ == "__main__":
    print("=" * 60)
    print("Session 生命周期测试")
    print("=" * 60)
    test_session_lifecycle()
    print("\n✅ 所有测试完成！")
