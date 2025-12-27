from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "white_bg_generator"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AI API
    GEMINI_API_KEY: str = ""

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Backend Server - 用于构建完整的图片 URL
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8001

    class Config:
        # 优先从环境变量读取，然后从 backend/.env 读取
        # 使用绝对路径确保无论从哪里运行都能正确读取
        env_file = os.environ.get("APP_ENV_FILE", os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
