"""
数据库迁移脚本 - 添加用户新字段
"""
import pymysql
from app.config import get_settings

settings = get_settings()


def migrate():
    """执行数据库迁移"""
    print("正在连接数据库...")

    conn = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        charset='utf8mb4'
    )

    try:
        with conn.cursor() as cursor:
            print("添加 username 字段...")
            try:
                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN username VARCHAR(50) NOT NULL DEFAULT '' AFTER hashed_password
                """)
                print("  ✓ username 字段添加成功")
            except pymysql.err.OperationalError as e:
                if 'Duplicate column name' in str(e):
                    print("  ⊙ username 字段已存在")
                else:
                    raise

            print("添加 user_code 字段...")
            try:
                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN user_code VARCHAR(20) NULL AFTER username
                """)
                print("  ✓ user_code 字段添加成功")
            except pymysql.err.OperationalError as e:
                if 'Duplicate column name' in str(e):
                    print("  ⊙ user_code 字段已存在")
                else:
                    raise

            print("添加 theme 字段...")
            try:
                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN theme VARCHAR(10) NOT NULL DEFAULT 'auto' AFTER user_code
                """)
                print("  ✓ theme 字段添加成功")
            except pymysql.err.OperationalError as e:
                if 'Duplicate column name' in str(e):
                    print("  ⊙ theme 字段已存在")
                else:
                    raise

            print("创建 username 唯一索引...")
            try:
                cursor.execute("CREATE UNIQUE INDEX ix_users_username ON users(username)")
                print("  ✓ 索引创建成功")
            except pymysql.err.OperationalError:
                print("  ⊙ 索引已存在")

            print("创建 user_code 唯一索引...")
            try:
                cursor.execute("CREATE UNIQUE INDEX ix_users_user_code ON users(user_code)")
                print("  ✓ 索引创建成功")
            except pymysql.err.OperationalError:
                print("  ⊙ 索引已存在")

        conn.commit()
        print("\n✅ 数据库迁移完成！")

    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
