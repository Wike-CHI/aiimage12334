"""
Pydantic 模型定义
用于 API 请求和响应验证
"""
from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional
from datetime import datetime
from app.models import TaskStatus


# ============ 用户相关 Schema ============

class UserCreate(BaseModel):
    """用户注册请求"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    username: str = Field(..., min_length=2, max_length=50)


class UserLogin(BaseModel):
    """用户登录请求"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    email: str
    username: str
    user_code: Optional[str] = None
    theme: str
    credits: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户更新请求"""
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    theme: Optional[str] = None  # light/dark/auto


# ============ Token 相关 Schema ============

class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 数据"""
    user_id: Optional[int] = None


# ============ 任务相关 Schema ============

class GenerationTaskCreate(BaseModel):
    """任务创建请求（预留）"""
    width: int = Field(1024, ge=100, le=4096)
    height: int = Field(1024, ge=100, le=4096)


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    id: int
    status: str
    progress: int = Field(0, ge=0, le=100)
    created_at: datetime
    updated_at: Optional[datetime] = None
    original_image_url: Optional[str] = None
    result_image_url: Optional[str] = None
    error_message: Optional[str] = None
    width: int
    height: int
    credits_used: int
    is_timed_out: bool = False
    can_retry: bool = False

    @field_validator('original_image_url', 'result_image_url', mode='before')
    @classmethod
    def add_base_url(cls, v, info):
        if v and not v.startswith('http'):
            from app.config import get_settings
            settings = get_settings()
            base_url = f"http://{settings.DB_HOST}:8000" if settings.DB_HOST != 'localhost' else "http://localhost:8000"
            v = f"{base_url}/{v}"
        return v

    class Config:
        from_attributes = True


class TaskSubmitResponse(BaseModel):
    """任务提交响应"""
    task_id: str
    status: str  # pending, processing, completed, failed, timeout
    message: str
    estimated_time: int  # 预计完成时间（秒）
    db_task_id: int


class TaskHistoryResponse(BaseModel):
    """任务历史响应"""
    tasks: list[TaskStatusResponse]
    total: int


class RetryTaskResponse(BaseModel):
    """任务重试响应"""
    task_id: str
    status: str
    message: str
    original_task_id: int


# ============ 积分相关 Schema ============

class CreditResponse(BaseModel):
    """积分响应"""
    credits: int


class CreditTransaction(BaseModel):
    """积分交易记录"""
    id: int
    user_id: int
    amount: int
    transaction_type: str  # earn, spend, refund
    description: Optional[str] = None
    created_at: datetime


# ============ 通用响应 Schema ============

class APIResponse(BaseModel):
    """通用 API 响应"""
    success: bool
    message: str
    data: Optional[dict] = None


class PaginationParams(BaseModel):
    """分页参数"""
    skip: int = 0
    limit: int = 20


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[dict] = None


# ============ 图片生成请求 Schema ============

class ImageGenerationParams(BaseModel):
    """图片生成参数"""
    width: int = Field(1024, ge=100, le=4096, description="输出图片宽度")
    height: int = Field(1024, ge=100, le=4096, description="输出图片高度")
    ratio: str = Field("1:1", pattern=r"^\d+:\d+$", description="宽高比")


class GenerationResult(BaseModel):
    """生成结果"""
    task_id: str
    status: str
    result_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    processing_time: Optional[float] = None  # 处理时间（秒）


# ============ 队列状态 Schema ============

class QueueStats(BaseModel):
    """队列统计"""
    total_tasks: int
    pending: int
    processing: int
    completed: int
    failed: int
    timeout: int
    cancelled: int


class HealthCheck(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    database: str
    queue: QueueStats
    uptime: float  # 运行时间（秒）
