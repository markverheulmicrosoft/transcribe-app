"""
Configuration settings for the Transcribe App.
Loads settings from environment variables.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
    # Azure OpenAI Configuration
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_name: str = "gpt-4o-transcribe-diarize"
    
    # Application settings
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 25  # gpt-4o-transcribe-diarize limit is 25MB
    
    # Default language for transcription
    default_language: str = "nl"  # Dutch as default for Raad van State


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
