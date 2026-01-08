#!/usr/bin/env python3
"""
数据库迁移：为generation_tasks表添加progress字段
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.config import get_settings

def migrate():
    """执行迁移"""
    settings = get_settings()
    
    # 构建数据库URL
    database_url = (
        f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
        f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    )
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # 检查字段是否已存在
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :db_name
            AND TABLE_NAME = 'generation_tasks'
            AND COLUMN_NAME = 'progress'
        """), {"db_name": settings.MYSQL_DATABASE})
        
        exists = result.fetchone()[0] > 0
        
        if exists:
            print("⚠️  progress字段已存在，跳过迁移")
            return
        
        # 添加progress字段
        print("📝 添加progress字段到generation_tasks表...")
        conn.execute(text("""
            ALTER TABLE generation_tasks
            ADD COLUMN progress INT DEFAULT 0
            COMMENT '任务进度 0-100'
            AFTER height
        """))
        conn.commit()
        
        print("✅ 迁移完成！progress字段已添加")
        
        # 更新现有任务的进度
        print("📝 更新现有已完成任务的进度...")
        conn.execute(text("""
            UPDATE generation_tasks
            SET progress = 100
            WHERE status = 'completed' AND progress = 0
        """))
        conn.commit()
        
        print("✅ 已更新现有已完成任务的进度为100%")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        sys.exit(1)
