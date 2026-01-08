"""
检查数据库中的用户账号
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import SessionLocal
from app.models import User

def check_user(email_or_username):
    """检查用户是否存在"""
    db = SessionLocal()
    try:
        # 尝试通过邮箱查找
        user = db.query(User).filter(User.email == email_or_username).first()
        if user:
            print(f"✅ 找到用户（通过邮箱）:")
            print(f"   ID: {user.id}")
            print(f"   用户名: {user.username}")
            print(f"   邮箱: {user.email}")
            print(f"   积分: {user.credits}")
            print(f"   是否激活: {user.is_active}")
            print(f"   创建时间: {user.created_at}")
            return True
        
        # 尝试通过用户名查找
        user = db.query(User).filter(User.username == email_or_username).first()
        if user:
            print(f"✅ 找到用户（通过用户名）:")
            print(f"   ID: {user.id}")
            print(f"   用户名: {user.username}")
            print(f"   邮箱: {user.email}")
            print(f"   积分: {user.credits}")
            print(f"   是否激活: {user.is_active}")
            print(f"   创建时间: {user.created_at}")
            return True
        
        print(f"❌ 未找到用户: {email_or_username}")
        return False
    finally:
        db.close()

def list_all_users():
    """列出所有用户"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"\n📋 数据库中共有 {len(users)} 个用户:")
        print("-" * 80)
        for user in users:
            print(f"ID: {user.id:3d} | 用户名: {user.username:20s} | 邮箱: {user.email:30s} | 积分: {user.credits}")
        print("-" * 80)
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 80)
    print("数据库用户查询")
    print("=" * 80)
    
    # 检查特定用户
    target_email = "226002618@nbu.edu.cn"
    print(f"\n🔍 查找用户: {target_email}")
    check_user(target_email)
    
    # 列出所有用户
    list_all_users()
