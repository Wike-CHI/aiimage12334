"""
一键清空数据库脚本
警告：此操作将删除所有任务记录，无法恢复！
"""
import sys
import os

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import engine, SessionLocal
from app.models import GenerationTask, User
from sqlalchemy import text


def clear_all_tasks():
    """清空所有任务记录"""
    db = SessionLocal()
    try:
        # 获取任务数量
        task_count = db.query(GenerationTask).count()
        if task_count == 0:
            print("数据库中没有任务记录")
            return

        print(f"警告：即将删除 {task_count} 条任务记录！")
        print("此操作无法撤销！")

        confirm = input("确定要继续吗？(输入 DELETE 确认): ")
        if confirm != "DELETE":
            print("操作已取消")
            return

        # 删除所有任务
        db.query(GenerationTask).delete()
        db.commit()
        print(f"已成功删除 {task_count} 条任务记录")

    except Exception as e:
        db.rollback()
        print(f"操作失败: {e}")
    finally:
        db.close()


def clear_user_tasks(user_id: int):
    """清空指定用户的任务记录"""
    db = SessionLocal()
    try:
        # 获取该用户的任务数量
        task_count = db.query(GenerationTask).filter(
            GenerationTask.user_id == user_id
        ).count()

        if task_count == 0:
            print(f"用户 {user_id} 没有任务记录")
            return

        print(f"警告：即将删除用户 {user_id} 的 {task_count} 条任务记录！")
        print("此操作无法撤销！")

        confirm = input("确定要继续吗？(输入 DELETE 确认): ")
        if confirm != "DELETE":
            print("操作已取消")
            return

        # 删除该用户的任务
        db.query(GenerationTask).filter(
            GenerationTask.user_id == user_id
        ).delete()
        db.commit()
        print(f"已成功删除用户 {user_id} 的 {task_count} 条任务记录")

    except Exception as e:
        db.rollback()
        print(f"操作失败: {e}")
    finally:
        db.close()


def reset_database():
    """完全重置数据库（删除所有表并重新创建）"""
    print("警告：此操作将删除所有数据库表并重新创建！")
    print("这将删除所有任务和用户数据！")

    confirm = input("确定要继续吗？(输入 RESET 确认): ")
    if confirm != "RESET":
        print("操作已取消")
        return

    from app.database import Base
    from app.models import User, GenerationTask

    db = SessionLocal()
    try:
        # 删除所有表
        Base.metadata.drop_all(bind=engine)
        print("已删除所有表")

        # 重新创建表
        Base.metadata.create_all(bind=engine)
        print("已重新创建所有表")

        print("数据库已重置完成")

    except Exception as e:
        db.rollback()
        print(f"操作失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("数据库清理工具")
    print("=" * 50)
    print("1. 清空所有任务记录")
    print("2. 清空指定用户的任务记录")
    print("3. 完全重置数据库（危险！）")
    print("4. 退出")
    print("=" * 50)

    choice = input("请选择操作 (1-4): ")

    if choice == "1":
        clear_all_tasks()
    elif choice == "2":
        user_id = input("请输入用户ID: ")
        try:
            clear_user_tasks(int(user_id))
        except ValueError:
            print("无效的用户ID")
    elif choice == "3":
        reset_database()
    elif choice == "4":
        print("已退出")
    else:
        print("无效选择")

