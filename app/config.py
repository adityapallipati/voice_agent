import os
import secrets
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, PostgresDsn, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application settings
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_WORKERS: int = 4
    LOG_LEVEL: str = "info"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "db"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            path=f"/{os.getenv('POSTGRES_DB', 'voice_agent')}"
        )
    
    # API Keys
    VAPI_API_KEY: str
    ANTHROPIC_API_KEY: str
    
    # N8N Settings
    N8N_URL: str = "http://n8n:5678"
    N8N_API_KEY: Optional[str] = None
    
    # CRM Integration
    CRM_TYPE: str = "none"
    CRM_API_URL: Optional[str] = None
    CRM_API_KEY: Optional[str] = None
    
    # Phone Settings
    DEFAULT_PHONE_NUMBER: Optional[str] = None
    CUSTOMER_SERVICE_NUMBER: Optional[str] = None
    
    # Storage Settings
    PROMPT_TEMPLATES_DIR: str = "./prompts"
    KNOWLEDGE_BASE_DIR: str = "./knowledge_base"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create settings instance
settings = Settings()