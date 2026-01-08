"""
统一错误处理模块
提供错误类型枚举和AppException异常类
"""
from enum import Enum
from typing import Optional
from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    """应用错误码"""
    # 积分相关
    CREDITS_INSUFFICIENT = "CREDITS_INSUFFICIENT"
    CREDITS_EXPIRED = "CREDITS_EXPIRED"

    # 图片处理相关
    IMAGE_PROCESSING_FAILED = "IMAGE_PROCESSING_FAILED"
    INVALID_IMAGE_FORMAT = "INVALID_IMAGE_FORMAT"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    IMAGE_DOWNLOAD_FAILED = "IMAGE_DOWNLOAD_FAILED"
    IMAGE_SAVE_FAILED = "IMAGE_SAVE_FAILED"

    # API相关
    API_KEY_MISSING = "API_KEY_MISSING"
    API_KEY_INVALID = "API_KEY_INVALID"
    API_RATE_LIMITED = "API_RATE_LIMITED"
    API_TIMEOUT = "API_TIMEOUT"

    # 任务相关
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_CANCELLED = "TASK_CANCELLED"
    TASK_TIMEOUT = "TASK_TIMEOUT"
    TASK_RETRY_FAILED = "TASK_RETRY_FAILED"

    # 验证相关
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # 服务器相关
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"

    # 网络相关
    NETWORK_ERROR = "NETWORK_ERROR"
    UPLOAD_FAILED = "UPLOAD_FAILED"


class AppException(HTTPException):
    """应用自定义异常"""

    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode | str,
        message: str,
        user_action: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code if isinstance(error_code, str) else error_code.value
        self.message = message
        self.user_action = user_action
        self.details = details

    def to_dict(self) -> dict:
        """转换为字典响应"""
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
            "user_action": self.user_action,
            "details": self.details,
        }


def create_error_response(
    error_code: ErrorCode | str,
    message: str,
    user_action: Optional[str] = None,
    details: Optional[dict] = None,
) -> dict:
    """创建标准错误响应"""
    return {
        "success": False,
        "error_code": error_code if isinstance(error_code, str) else error_code.value,
        "message": message,
        "user_action": user_action,
        "details": details,
    }


# ============ 便捷错误创建函数 ============

def credits_insufficient_error(required: int, available: int) -> AppException:
    """积分不足错误"""
    return AppException(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=ErrorCode.CREDITS_INSUFFICIENT,
        message=f"积分不足，需要 {required} 积分，当前可用 {available} 积分",
        user_action="请前往充值页面购买积分后重试",
        details={"required": required, "available": available}
    )


def invalid_image_format_error(content_type: str) -> AppException:
    """图片格式错误"""
    return AppException(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=ErrorCode.INVALID_IMAGE_FORMAT,
        message=f"不支持的文件格式: {content_type}",
        user_action="请上传 JPG、PNG 或 WebP 格式的图片",
        details={"content_type": content_type}
    )


def image_too_large_error(size_mb: float, max_mb: float = 10) -> AppException:
    """图片过大错误"""
    return AppException(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=ErrorCode.IMAGE_TOO_LARGE,
        message=f"图片大小({size_mb:.1f}MB)超过限制({max_mb}MB)",
        user_action=f"请上传小于 {max_mb}MB 的图片",
        details={"size_mb": size_mb, "max_mb": max_mb}
    )


def image_processing_failed_error(detail: str) -> AppException:
    """图片处理失败错误"""
    return AppException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCode.IMAGE_PROCESSING_FAILED,
        message=f"图片处理失败: {detail}",
        user_action="请尝试重新上传图片，或联系客服获取帮助",
        details={"detail": detail}
    )


def api_error(error_code: ErrorCode, message: str, user_action: str) -> AppException:
    """API相关错误"""
    status_map = {
        ErrorCode.API_KEY_MISSING: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.API_KEY_INVALID: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.API_RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
        ErrorCode.API_TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
    }
    return AppException(
        status_code=status_map.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR),
        error_code=error_code,
        message=message,
        user_action=user_action,
    )


def task_not_found_error(task_id: int) -> AppException:
    """任务不存在错误"""
    return AppException(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code=ErrorCode.TASK_NOT_FOUND,
        message=f"任务 #{task_id} 不存在或已被删除",
        user_action="请刷新页面后重试",
        details={"task_id": task_id}
    )


def network_error_error(detail: str = "网络连接失败") -> AppException:
    """网络错误"""
    return AppException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        error_code=ErrorCode.NETWORK_ERROR,
        message=detail,
        user_action="请检查网络连接后重试，如果问题持续存在，请稍后再试",
    )


def validation_error_error(message: str, details: Optional[dict] = None) -> AppException:
    """验证错误"""
    return AppException(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=ErrorCode.VALIDATION_ERROR,
        message=message,
        user_action="请检查输入后重试",
        details=details
    )


def internal_error_error(detail: str = "服务内部错误") -> AppException:
    """内部错误"""
    return AppException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCode.INTERNAL_ERROR,
        message=detail,
        user_action="如果问题持续存在，请联系管理员",
    )
