import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "career_profiling_db")
    
    # App
    APP_NAME: str = "Career Profiling Platform"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # AI
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "gpt-4")
    AI_API_BASE: str = os.getenv("AI_API_BASE", "https://api.openai.com/v1")
    
    # Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

