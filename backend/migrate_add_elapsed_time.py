#!/usr/bin/env python3
"""
数据库迁移脚本：添加 elapsed_time 字段到 generation_tasks 表

使用方法:
    python migrate_add_elapsed_time.py

注意事项:
    - 需要配置数据库连接信息
    - 运行前建议备份数据库
"""

import sys
import os

# 添加后端路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, Column, Float
from sqlalchemy.orm import sessionmaker

# 数据库配置 - 请根据实际情况修改
# 格式: mysql+pymysql://用户名:密码@主机:端口/数据库名
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:your_password@localhost:3306/aiimage"
)


def run_migration():
    """执行迁移"""
    print("=" * 60)
    print("数据库迁移: 添加 elapsed_time 字段")
    print("=" * 60)
    print(f"数据库连接: {DATABASE_URL.split('@')[0]}@... (密码已隐藏)")
    print()

    # 创建数据库引擎
    engine = create_engine(DATABASE_URL, echo=False)

    try:
        # 测试连接
        with engine.connect() as conn:
            print("✓ 数据库连接成功")

        # 检查字段是否已存在
        with engine.connect() as conn:
            result = conn.execute(text("SHOW COLUMNS FROM generation_tasks LIKE 'elapsed_time'"))
            column_exists = result.fetchone() is not None

            if column_exists:
                print("⚠ elapsed_time 字段已存在，无需迁移")
                return True

        # 执行 ALTER TABLE
        with engine.connect() as conn:
            print("正在添加 elapsed_time 字段...")
            conn.execute(text("ALTER TABLE generation_tasks ADD COLUMN elapsed_time FLOAT"))
            conn.commit()
            print("✓ 字段添加成功")

        # 验证字段
        with engine.connect() as conn:
            result = conn.execute(text("SHOW COLUMNS FROM generation_tasks LIKE 'elapsed_time'"))
            column = result.fetchone()
            if column:
                print(f"✓ 验证成功: {column[0]} ({column[1]})")
            else:
                print("✗ 验证失败：字段未找到")
                return False

        print()
        print("=" * 60)
        print("迁移完成!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        print()
        print("可能的原因:")
        print("  1. 数据库连接信息错误")
        print("  2. 数据库权限不足")
        print("  3. 表名或字段名冲突")
        print()
        print("请检查 DATABASE_URL 环境变量或手动执行 SQL:")
        print("  ALTER TABLE generation_tasks ADD COLUMN elapsed_time FLOAT;")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
