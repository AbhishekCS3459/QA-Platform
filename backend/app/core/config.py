"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Q&A Dashboard API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    DATABASE_URL: str
    TIMESCALE_SERVICE_URL: str

    SECRET_KEY: str = "secret"      
    
   
    GROQ_API_KEY: str = ""  
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  
    GROQ_TEMPERATURE: float = 1.0
    GROQ_MAX_COMPLETION_TOKENS: int = 8192
    GROQ_TOP_P: float = 1.0
    GROQ_REASONING_EFFORT: Optional[str] = None 

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2" 
    
 
    VECTOR_TABLE_NAME: str = "question_embeddings"
    VECTOR_EMBEDDING_DIMENSIONS: int = 384 

    CORS_ORIGINS: str = ""     

    def cors_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  


settings = Settings()
