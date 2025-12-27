from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models import TaskStatus


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    credits: int
    created_at: datetime

    class Config:
        from_attributes = True


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
