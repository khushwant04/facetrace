"""
Application configuration - Optimized for AWS Rekognition + Neon DB
"""
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Student Face Recognition SaaS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database (Neon PostgreSQL)
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # Auth0
    AUTH0_DOMAIN: str
    AUTH0_API_AUDIENCE: str
    AUTH0_CLIENT_ID: Optional[str] = None
    AUTH0_CLIENT_SECRET: Optional[str] = None
    AUTH0_ISSUER: Optional[str] = None
    AUTH0_ALGORITHMS: list[str] = ["RS256"]
    
    # AWS
    AWS_REGION: str = "ap-south-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # S3
    S3_BUCKET_NAME: str
    
    # Rekognition
    REKOGNITION_COLLECTION_ID: str = "student-faces-prod"
    
    # Redis Cache
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_USERNAME: str = "default"
    REDIS_PASSWORD: str = ""
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000"
    ]
    
    # Multi-tenancy
    TENANT_HEADER_NAME: str = "X-Organization-ID"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @model_validator(mode="after")
    def _ensure_issuer(self):
        if not self.AUTH0_ISSUER and getattr(self, "AUTH0_DOMAIN", None):
            domain = self.AUTH0_DOMAIN.rstrip('/')
            self.AUTH0_ISSUER = f"https://{domain}/"
        return self


settings = Settings()
