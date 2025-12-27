"""
任务队列服务
提供异步任务处理、超时管理、错误处理和状态追踪
"""
import asyncio
import uuid
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 等待处理
    PROCESSING = "processing" # 正在处理
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    TIMEOUT = "timeout"       # 超时
    CANCELLED = "cancelled"   # 已取消


class TaskInfo:
    """任务信息类"""

    def __init__(
        self,
        task_id: str,
        user_id: int,
        status: TaskStatus = TaskStatus.PENDING,
        progress: int = 0,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
        created_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        timeout_seconds: int = 300  # 默认5分钟超时
    ):
        self.task_id = task_id
        self.user_id = user_id
        self.status = status
        self.progress = progress
        self.result = result
        self.error_message = error_message
        self.created_at = created_at or datetime.now()
        self.started_at = started_at
        self.completed_at = completed_at
        self.timeout_seconds = timeout_seconds
        self._future = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "progress": self.progress,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeout_seconds": self.timeout_seconds,
            "is_timed_out": self.is_timed_out()
        }

    def is_timed_out(self) -> bool:
        """检查是否超时"""
        if self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        if self.started_at is None:
            return False
        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds

    @property
    def is_completed(self) -> bool:
        """是否已完成（成功或失败）"""
        return self.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.TIMEOUT,
            TaskStatus.CANCELLED
        ]

    @property
    def is_active(self) -> bool:
        """是否处于活动状态"""
        return self.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]


class TaskQueue:
    """
    异步任务队列
    支持任务提交、状态追踪、超时管理和错误处理
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

        self._tasks: Dict[str, TaskInfo] = {}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="task_worker")
        self._cleanup_task = None
        self._lock = threading.RLock()
        self._initialized = True
        self._start_cleanup()

    def submit_task(
        self,
        user_id: int,
        task_func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        timeout_seconds: int = 300
    ) -> TaskInfo:
        """
        提交任务到队列

        Args:
            user_id: 用户ID
            task_func: 要执行的函数
            args: 位置参数
            kwargs: 关键字参数
            timeout_seconds: 超时时间（秒）

        Returns:
            TaskInfo: 任务信息对象
        """
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            user_id=user_id,
            status=TaskStatus.PENDING,
            timeout_seconds=timeout_seconds
        )

        with self._lock:
            self._tasks[task_id] = task_info

        # 在线程池中执行任务
        self._executor.submit(
            self._run_task,
            task_id,
            task_func,
            args,
            kwargs or {}
        )

        logger.info(f"Task {task_id} submitted for user {user_id}")
        return task_info

    def _run_task(
        self,
        task_id: str,
        task_func: Callable,
        args: tuple,
        kwargs: dict
    ):
        """内部任务执行方法"""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                logger.error(f"Task {task_id} not found")
                return

        try:
            # 更新状态为处理中
            task_info.status = TaskStatus.PROCESSING
            task_info.started_at = datetime.now()
            task_info.progress = 10  # 开始处理，进度10%

            logger.info(f"Task {task_id} started")

            # 执行实际任务（带超时）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 使用 asyncio.wait_for 实现超时控制
                future = loop.run_in_executor(
                    self._executor,
                    lambda: task_func(*args, **kwargs)
                )

                # 设置超时
                result = loop.run_until_complete(
                    asyncio.wait_for(
                        future,
                        timeout=task_info.timeout_seconds
                    )
                )

                task_info.progress = 100
                task_info.status = TaskStatus.COMPLETED
                task_info.result = result
                task_info.completed_at = datetime.now()

                logger.info(f"Task {task_id} completed successfully")

            except asyncio.TimeoutError:
                task_info.status = TaskStatus.TIMEOUT
                task_info.error_message = f"Task timed out after {task_info.timeout_seconds} seconds"
                task_info.completed_at = datetime.now()
                logger.warning(f"Task {task_id} timed out")

            except Exception as e:
                task_info.status = TaskStatus.FAILED
                task_info.error_message = f"Task execution failed: {str(e)}"
                task_info.completed_at = datetime.now()
                logger.error(f"Task {task_id} failed: {str(e)}")

            finally:
                loop.close()

        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.error_message = f"Task queue error: {str(e)}"
            task_info.completed_at = datetime.now()
            logger.error(f"Task {task_id} queue error: {str(e)}")

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        with self._lock:
            return self._tasks.get(task_id)

    def get_user_tasks(self, user_id: int, include_completed: bool = True) -> list:
        """
        获取用户的所有任务

        Args:
            user_id: 用户ID
            include_completed: 是否包含已完成的任务

        Returns:
            list: 任务列表
        """
        with self._lock:
            tasks = []
            for task_info in self._tasks.values():
                if task_info.user_id == user_id:
                    if include_completed or not task_info.is_completed:
                        tasks.append(task_info)
            return sorted(tasks, key=lambda x: x.created_at, reverse=True)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if task_info and task_info.is_active:
                task_info.status = TaskStatus.CANCELLED
                task_info.completed_at = datetime.now()
                logger.info(f"Task {task_id} cancelled")
                return True
            return False

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            tasks_to_remove = []

            for task_id, task_info in self._tasks.items():
                if task_info.completed_at and task_info.completed_at < cutoff:
                    tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self._tasks[task_id]
                logger.info(f"Cleaned up old task {task_id}")

            return len(tasks_to_remove)

    def _start_cleanup(self):
        """启动定期清理任务"""
        async def periodic_cleanup():
            while True:
                await asyncio.sleep(3600)  # 每小时清理一次
                count = self.cleanup_old_tasks()
                if count > 0:
                    logger.info(f"Cleaned up {count} old tasks")

        import threading
        thread = threading.Thread(target=lambda: asyncio.run(periodic_cleanup()), daemon=True)
        thread.start()

    def get_queue_stats(self) -> dict:
        """获取队列统计信息"""
        with self._lock:
            stats = {
                "total_tasks": len(self._tasks),
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "timeout": 0,
                "cancelled": 0
            }

            for task_info in self._tasks.values():
                status_key = task_info.status.value if isinstance(task_info.status, TaskStatus) else task_info.status
                if status_key in stats:
                    stats[status_key] += 1

            return stats


# 全局任务队列实例
task_queue = TaskQueue()

