"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    PROJECT_NAME: str = "Q&A Dashboard API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    ENVIRONMENT: str = Field(default="development")
    
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/postgres"
    )
    
    SECRET_KEY: str = Field(
        default="secret"
    )
    
    cors_origins_str: str = Field(
        default="",
        alias="CORS_ORIGINS"
    )
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS_ORIGINS from comma-separated string"""
        if not self.cors_origins_str:
            return []
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

