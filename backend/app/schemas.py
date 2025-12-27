from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from app.models import TaskStatus


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
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
    username: Optional[str] = None
    theme: Optional[str] = None  # light/dark/auto


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Task schemas
class GenerationTaskCreate(BaseModel):
    width: int = 1024
    height: int = 1024


class GenerationTaskResponse(BaseModel):
    id: int
    user_id: int
    original_image_url: Optional[str]
    result_image_url: Optional[str]
    status: TaskStatus
    credits_used: int
    width: int
    height: int
    created_at: datetime

    @field_validator('original_image_url', 'result_image_url', mode='before')
    @classmethod
    def add_base_url(cls, v, info):
        if v and not v.startswith('http'):
            from app.config import get_settings
            settings = get_settings()
            # 使用 API 服务器地址
            base_url = f"http://{settings.DB_HOST}:8000" if settings.DB_HOST != 'localhost' else "http://localhost:8000"
            v = f"{base_url}/{v}"
        return v

    class Config:
        from_attributes = True


class TaskHistoryResponse(BaseModel):
    tasks: list[GenerationTaskResponse]
    total: int


# Credit schemas
class CreditResponse(BaseModel):
    credits: int


# API Response
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
