"""
WebSocket 连接管理器
提供任务进度实时推送功能
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class TaskProgressData:
    """任务进度数据"""
    task_id: int
    status: str  # pending, processing, completed, failed
    progress: int = 0  # 0-100
    result_image_url: Optional[str] = None
    elapsed_time: Optional[float] = None
    estimated_remaining_seconds: Optional[int] = None
    error_message: Optional[str] = None
    updated_at: datetime = field(default_factory=datetime.now)


class ConnectionManager:
    """
    WebSocket 连接管理器 - 单例模式
    支持用户多设备连接，自动处理断开连接
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # user_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # WebSocket -> user_id (反向映射)
        self.connection_users: Dict[WebSocket, int] = {}
        self._lock = asyncio.Lock()
        self._initialized = True

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """
        建立 WebSocket 连接

        Args:
            websocket: FastAPI WebSocket 连接
            user_id: 用户 ID
        """
        await websocket.accept()

        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            self.connection_users[websocket] = user_id

        logger.info(f"WebSocket connected: user_id={user_id}, total_connections={len(self.active_connections.get(user_id, set()))}")

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """
        断开 WebSocket 连接

        Args:
            websocket: FastAPI WebSocket 连接
            user_id: 用户 ID
        """
        import asyncio

        async def _disconnect():
            async with self._lock:
                if user_id in self.active_connections:
                    self.active_connections[user_id].discard(websocket)
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]

                self.connection_users.pop(websocket, None)

                logger.info(f"WebSocket disconnected: user_id={user_id}")

        # 在事件循环中执行
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_disconnect())
            else:
                asyncio.run(_disconnect())
        except RuntimeError:
            # 没有事件循环，创建新的
            asyncio.run(_disconnect())

    async def send_personal_message(self, message: dict, user_id: int) -> int:
        """
        向用户的所有连接发送消息

        Args:
            message: 消息内容（字典，会自动转为 JSON）
            user_id: 用户 ID

        Returns:
            成功发送的连接数量
        """
        async with self._lock:
            connections = self.active_connections.get(user_id, set()).copy()

        if not connections:
            return 0

        sent_count = 0
        text_message = json.dumps(message, default=str)

        for connection in connections:
            try:
                await connection.send_text(text_message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send message to connection: {e}")
                # 连接可能已断开，标记为待清理
                self.disconnect(connection, user_id)

        return sent_count

    async def broadcast_task_update(self, user_id: int, data: TaskProgressData) -> int:
        """
        广播任务进度更新

        Args:
            user_id: 用户 ID
            data: 任务进度数据

        Returns:
            成功发送的连接数量
        """
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

        return await self.send_personal_message(message, user_id)

    async def broadcast_task_complete(self, user_id: int, task_id: int, data: TaskProgressData) -> int:
        """
        广播任务完成消息

        Args:
            user_id: 用户 ID
            task_id: 任务 ID
            data: 任务完成数据

        Returns:
            成功发送的连接数量
        """
        message = {
            "type": "task_complete",
            "task_id": task_id,
            "data": {
                "status": data.status,
                "progress": data.progress,
                "result_image_url": data.result_image_url,
                "elapsed_time": data.elapsed_time,
                "updated_at": data.updated_at.isoformat()
            }
        }

        return await self.send_personal_message(message, user_id)

    async def broadcast_task_failed(self, user_id: int, task_id: int, error_message: str) -> int:
        """
        广播任务失败消息

        Args:
            user_id: 用户 ID
            task_id: 任务 ID
            error_message: 错误信息

        Returns:
            成功发送的连接数量
        """
        message = {
            "type": "task_failed",
            "task_id": task_id,
            "data": {
                "status": "failed",
                "progress": 0,
                "error_message": error_message,
                "updated_at": datetime.now().isoformat()
            }
        }

        return await self.send_personal_message(message, user_id)

    def get_connection_count(self, user_id: int) -> int:
        """
        获取用户的连接数量

        Args:
            user_id: 用户 ID

        Returns:
            连接数量
        """
        return len(self.active_connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """
        获取总连接数

        Returns:
            所有用户的连接总数
        """
        return sum(len(connections) for connections in self.active_connections.values())


# 全局 WebSocket 管理器实例
ws_manager = ConnectionManager()
