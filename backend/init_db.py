"""
数据库初始化脚本
"""
import pymysql
from app.config import get_settings
from app.models import Base
from app.database import engine

settings = get_settings()


def init_database():
    """创建数据库和表"""
    # 连接 MySQL 服务器
    conn = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        charset='utf8mb4'
    )

    try:
        with conn.cursor() as cursor:
            # 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"数据库 {settings.DB_NAME} 创建成功")

        conn.commit()

        # 创建表
        Base.metadata.create_all(bind=engine)
        print("数据表创建成功")

    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
    print("数据库初始化完成！")
