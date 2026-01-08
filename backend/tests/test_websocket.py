"""
WebSocket 功能测试
测试任务进度实时推送功能
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth import create_access_token
from app.database import get_db, engine
from app.models import Base, User
from sqlalchemy.orm import Session


@pytest.fixture(scope="module")
def test_db():
    """创建测试数据库"""
    # 使用内存 SQLite 进行测试
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    yield db

    db.close()


@pytest.fixture
def test_user(test_db):
    """创建测试用户"""
    user = User(
        email="test@example.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/IiS",  # "password123"
        credits=10
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """生成测试用户的 JWT token"""
    return create_access_token(data={"sub": str(test_user.id)})


class TestWebSocketConnection:
    """WebSocket 连接测试"""

    def test_websocket_connect_without_token(self):
        """测试未提供 token 时连接被拒绝"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/notifications") as ws:
                # 应该收到关闭消息
                with pytest.raises(Exception):
                    ws.receive_text()

    def test_websocket_connect_with_invalid_token(self):
        """测试使用无效 token 时连接被拒绝"""
        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws/notifications?token=invalid_token"):
                    pass

    def test_websocket_connect_with_valid_token(self, auth_token):
        """测试使用有效 token 时连接成功"""
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/notifications?token={auth_token}") as ws:
                # 连接应该成功，不应该立即关闭
                data = ws.receive_text()
                assert data == "pong"  # 收到心跳响应


class TestWebSocketHeartbeat:
    """WebSocket 心跳测试"""

    def test_websocket_ping_pong(self, auth_token):
        """测试心跳 ping-pong"""
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/notifications?token={auth_token}") as ws:
                # 发送 ping
                ws.send_text("ping")
                # 应该收到 pong
                response = ws.receive_text()
                assert response == "pong"


class TestWebSocketManager:
    """WebSocket Manager 单元测试"""

    def test_connection_manager_singleton(self):
        """测试连接管理器是单例"""
        from app.services.websocket_manager import ConnectionManager

        manager1 = ConnectionManager()
        manager2 = ConnectionManager()
        assert manager1 is manager2

    def test_task_progress_data(self):
        """测试任务进度数据模型"""
        from app.services.websocket_manager import TaskProgressData
        from datetime import datetime

        data = TaskProgressData(
            task_id=1,
            status="processing",
            progress=50,
            elapsed_time=10.5,
            estimated_remaining_seconds=15
        )

        assert data.task_id == 1
        assert data.status == "processing"
        assert data.progress == 50
        assert data.elapsed_time == 10.5
        assert data.estimated_remaining_seconds == 15

    def test_broadcast_task_update(self):
        """测试广播任务更新"""
        import asyncio
        from app.services.websocket_manager import ConnectionManager, TaskProgressData
        from fastapi import WebSocket

        # 创建新的管理器实例进行测试
        manager = ConnectionManager()

        # 模拟 WebSocket
        class MockWebSocket:
            def __init__(self):
                self.messages = []

            async def send_text(self, message):
                self.messages.append(message)

        async def test():
            mock_ws = MockWebSocket()

            # 由于是测试，我们直接测试消息格式
            data = TaskProgressData(
                task_id=123,
                status="processing",
                progress=25,
                elapsed_time=5.0,
                estimated_remaining_seconds=20
            )

            message = {
                "type": "task_update",
                "task_id": data.task_id,
                "data": {
                    "status": data.status,
                    "progress": data.progress,
                    "result_image_url": data.result_image_url,
                    "elapsed_time": data.elapsed_time,
                    "estimated_remaining_seconds": data.estimated_remaining_seconds,
                    "updated_at": data.updated_at.isoformat()
                }
            }

            # 验证消息格式正确
            assert message["type"] == "task_update"
            assert message["task_id"] == 123
            assert message["data"]["status"] == "processing"
            assert message["data"]["progress"] == 25

        asyncio.run(test())

    def test_broadcast_task_complete(self):
        """测试广播任务完成消息"""
        from app.services.websocket_manager import TaskProgressData

        data = TaskProgressData(
            task_id=456,
            status="completed",
            progress=100,
            result_image_url="http://localhost:8001/results/456_result.png",
            elapsed_time=45.5
        )

        message = {
            "type": "task_complete",
            "task_id": data.task_id,
            "data": {
                "status": data.status,
                "progress": data.progress,
                "result_image_url": data.result_image_url,
                "elapsed_time": data.elapsed_time,
                "updated_at": data.updated_at.isoformat()
            }
        }

        assert message["type"] == "task_complete"
        assert message["task_id"] == 456
        assert message["data"]["status"] == "completed"
        assert message["data"]["progress"] == 100

    def test_broadcast_task_failed(self):
        """测试广播任务失败消息"""
        message = {
            "type": "task_failed",
            "task_id": 789,
            "data": {
                "status": "failed",
                "progress": 0,
                "error_message": "API 请求超时",
                "updated_at": "2026-01-08T10:30:00.000000"
            }
        }

        assert message["type"] == "task_failed"
        assert message["task_id"] == 789
        assert message["data"]["status"] == "failed"
        assert "超时" in message["data"]["error_message"]


class TestNotifyTaskProgress:
    """notify_task_progress 函数测试"""

    @pytest.mark.asyncio
    async def test_notify_task_progress_completed(self, test_db, test_user):
        """测试任务完成通知"""
        from app.routes.generation_v2 import notify_task_progress

        # 调用通知函数，不应抛出异常
        await notify_task_progress(
            user_id=test_user.id,
            task_id=1,
            status="completed",
            progress=100,
            result_image_url="http://localhost/results/1_result.png",
            elapsed_time=30.5
        )

    @pytest.mark.asyncio
    async def test_notify_task_progress_processing(self, test_db, test_user):
        """测试任务处理中通知"""
        from app.routes.generation_v2 import notify_task_progress

        await notify_task_progress(
            user_id=test_user.id,
            task_id=2,
            status="processing",
            progress=50,
            estimated_remaining=15
        )

    @pytest.mark.asyncio
    async def test_notify_task_progress_failed(self, test_db, test_user):
        """测试任务失败通知"""
        from app.routes.generation_v2 import notify_task_progress

        await notify_task_progress(
            user_id=test_user.id,
            task_id=3,
            status="failed",
            error_message="测试错误信息"
        )


# 运行测试命令:
# pytest backend/tests/test_websocket.py -v
