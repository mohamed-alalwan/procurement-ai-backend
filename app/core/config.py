"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "AI Project"
    debug: bool = False
    
    class Config:
        env_file = ".env"


settings = Settings()
