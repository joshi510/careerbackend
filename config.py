from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ======================
    # Database (Render-ready)
    # ======================
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # =========
    # App
    # =========
    APP_NAME: str = "Career Profiling Platform"
    DEBUG: bool = Field(default=False, env="DEBUG")

    # =========
    # JWT
    # =========
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,
        env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # =========
    # AI
    # =========
    AI_API_KEY: str = Field(default="", env="AI_API_KEY")
    AI_MODEL: str = "gpt-4"
    AI_API_BASE: str = "https://api.openai.com/v1"

    # =========
    # Gemini
    # =========
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
