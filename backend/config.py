"""
Application configuration management
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:4321"]
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # AssemblyAI
    ASSEMBLYAI_API_KEY: str
    
    # Video Configuration
    MAX_VIDEO_SIZE_MB: int = 100
    SUPPORTED_VIDEO_FORMATS: str = "mp4,webm,mov"
    CDN_BASE_URL: str = "http://huydq.staging.mediacdn.vn"
    
    # TUS
    TUS_SERVER_URL: str = "http://10.3.16.62/v1/namespaces/huydq/tus"
    TUS_AUTH_TYPE: str = "application_credential"
    TUS_CREDENTIAL_ID: str = ""
    TUS_CREDENTIAL_SECRET: str = ""
    TUS_MAX_SIZE: int = 104857600
    
    # Application
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
