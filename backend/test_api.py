"""
后端 API 完整测试
"""
import os
import sys
import pytest
from datetime import timedelta
from unittest.mock import patch, AsyncMock, MagicMock

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User, GenerationTask, TaskStatus
from app.auth import (
    get_password_hash, verify_password, create_access_token, get_current_user
)
import bcrypt
from app.config import Settings


# ==================== 测试数据库配置 ====================

# 使用 SQLite 进行测试
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ==================== Fixture ====================

@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库表"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    hashed_password = get_password_hash("testpassword123")
    user = User(
        email="test@example.com",
        hashed_password=hashed_password,
        credits=10
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user, db_session):
    """生成测试用户的 JWT token"""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def auth_headers(auth_token):
    """生成带认证的请求头"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def sample_image(tmp_path):
    """创建测试用图片文件"""
    from PIL import Image
    image = Image.new('RGB', (100, 100), color='red')
    image_path = tmp_path / "test_image.jpg"
    image.save(str(image_path))
    return str(image_path)


# ==================== Auth 测试 ====================

class TestAuthAPI:
    """认证 API 测试"""

    def test_register_success(self, client):
        """测试用户注册成功"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client, test_user):
        """测试重复邮箱注册"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """测试无效邮箱格式"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "password": "password123"
            }
        )
        assert response.status_code == 422  # Validation error

    def test_login_success(self, client, test_user):
        """测试登录成功"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """测试密码错误"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """测试用户不存在"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 401

    def test_get_current_user(self, client, test_user, auth_headers):
        """测试获取当前用户信息"""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "credits" in data
        assert "id" in data

    def test_get_current_user_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_refresh_token(self, client, auth_headers):
        """测试刷新 token"""
        response = client.post("/api/auth/refresh", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


# ==================== Generation API 测试 ====================

class TestGenerationAPI:
    """图片生成 API 测试"""

    def test_get_credits(self, client, test_user, auth_headers):
        """测试获取用户积分"""
        response = client.get("/api/credits", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert data["credits"] == 10

    def test_get_credits_unauthorized(self, client):
        """测试未授权获取积分"""
        response = client.get("/api/credits")
        assert response.status_code == 401

    def test_get_task_history(self, client, test_user, db_session, auth_headers):
        """测试获取任务历史"""
        # 创建测试任务
        task = GenerationTask(
            user_id=test_user.id,
            original_image_url="/test/original.jpg",
            result_image_url="/test/result.jpg",
            status=TaskStatus.COMPLETED,
            credits_used=1
        )
        db_session.add(task)
        db_session.commit()

        response = client.get("/api/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_get_task_history_pagination(self, client, test_user, auth_headers):
        """测试任务历史分页"""
        response = client.get("/api/tasks?skip=0&limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) <= 5

    def test_get_task_detail(self, client, test_user, db_session, auth_headers):
        """测试获取任务详情"""
        task = GenerationTask(
            user_id=test_user.id,
            original_image_url="/test/original.jpg",
            result_image_url="/test/result.jpg",
            status=TaskStatus.COMPLETED,
            credits_used=1
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        response = client.get(f"/api/tasks/{task.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task.id
        assert data["status"] == "completed"

    def test_get_task_detail_not_found(self, client, test_user, auth_headers):
        """测试获取不存在的任务"""
        response = client.get("/api/tasks/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_get_task_detail_wrong_user(self, client, db_session, auth_headers):
        """测试获取其他用户的任务"""
        # 创建另一个用户
        other_user = User(
            email="other@example.com",
            hashed_password=get_password_hash("password"),
            credits=5
        )
        db_session.add(other_user)
        db_session.commit()

        # 创建该用户的任务
        task = GenerationTask(
            user_id=other_user.id,
            original_image_url="/test/other.jpg",
            status=TaskStatus.COMPLETED
        )
        db_session.add(task)
        db_session.commit()

        # 尝试用第一个用户访问
        response = client.get(f"/api/tasks/{task.id}", headers=auth_headers)
        assert response.status_code == 404


# ==================== Token 测试 ====================

class TestJWTToken:
    """JWT Token 测试"""

    def test_create_access_token(self):
        """测试创建 token"""
        token = create_access_token(data={"sub": "123"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """测试创建带过期时间的 token"""
        token = create_access_token(
            data={"sub": "123"},
            expires_delta=timedelta(hours=1)
        )
        assert token is not None

    def test_token_contains_payload(self):
        """测试 token 包含负载"""
        from jose import jwt
        from app.config import get_settings

        settings = get_settings()
        token = create_access_token(data={"sub": "456"})

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "456"
        assert "exp" in payload


# ==================== 密码哈希测试 ====================

class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt 前缀

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_same_password(self):
        """测试相同密码产生不同哈希（bcrypt 特性）"""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# ==================== 配置测试 ====================

class TestConfig:
    """配置测试"""

    def test_settings_defaults(self):
        """测试默认配置"""
        settings = Settings()
        assert settings.DB_HOST == "localhost"
        assert settings.DB_PORT == 3306
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.ALGORITHM == "HS256"

    def test_database_url_property(self):
        """测试数据库 URL 生成"""
        settings = Settings()
        url = settings.DATABASE_URL
        assert "mysql+pymysql://" in url
        assert settings.DB_NAME in url


# ==================== 模型测试 ====================

class TestModels:
    """数据模型测试"""

    def test_user_model_creation(self, db_session):
        """测试用户模型创建"""
        user = User(
            email="model_test@example.com",
            hashed_password=get_password_hash("password"),
            credits=5
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.email == "model_test@example.com"
        assert user.credits == 5
        assert user.created_at is not None

    def test_user_default_credits(self, db_session):
        """测试用户默认积分"""
        user = User(
            email="default_credits@example.com",
            hashed_password="hash"
        )
        db_session.add(user)
        db_session.commit()

        assert user.credits == 10  # 默认值

    def test_task_status_enum(self):
        """测试任务状态枚举"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.PROCESSING == "processing"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"

    def test_task_model_creation(self, db_session, test_user):
        """测试任务模型创建"""
        task = GenerationTask(
            user_id=test_user.id,
            original_image_url="/test/path/original.jpg",
            status=TaskStatus.PENDING
        )
        db_session.add(task)
        db_session.commit()

        assert task.id is not None
        assert task.user_id == test_user.id
        assert task.status == TaskStatus.PENDING
        assert task.credits_used == 1  # 默认值


# ==================== 健康检查测试 ====================

class TestHealthCheck:
    """健康检查测试"""

    def test_root_endpoint(self, client):
        """测试根路由"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["status"] == "running"

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


# ==================== Schema 验证测试 ====================

class TestSchemas:
    """Pydantic Schema 测试"""

    def test_user_create_schema(self):
        """测试用户创建 schema"""
        from app.schemas import UserCreate

        user = UserCreate(email="schema@test.com", password="password123")
        assert user.email == "schema@test.com"
        assert user.password == "password123"

    def test_user_response_schema(self):
        """测试用户响应 schema"""
        from datetime import datetime
        from app.schemas import UserResponse

        response = UserResponse(
            id=1,
            email="test@test.com",
            credits=10,
            created_at=datetime.now()
        )
        assert response.id == 1
        assert response.email == "test@test.com"

    def test_token_schema(self):
        """测试 token schema"""
        from app.schemas import Token

        token = Token(access_token="abc123")
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"  # 默认值

    def test_credit_response_schema(self):
        """测试积分响应 schema"""
        from app.schemas import CreditResponse

        credit = CreditResponse(credits=100)
        assert credit.credits == 100


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
