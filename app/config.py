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
    # Use the preview API version for diarization (diarized_json support).
    azure_openai_api_version: str = "2025-04-01-preview"
    # For gpt-4o-transcribe-diarize use 'diarized_json' to receive speaker labels.
    azure_openai_transcription_response_format: str = "diarized_json"
    # Diarization models require chunking_strategy; 'auto' is recommended.
    azure_openai_chunking_strategy_type: str | None = "auto"
    
    # Azure Speech Service Configuration (alternative transcription backend)
    azure_speech_key: str = ""
    azure_speech_region: str = "westeurope"  # e.g., westeurope, eastus
    
    # Transcription engine: "openai" or "speech" (Azure Speech Service)
    transcription_engine: str = "openai"
    
    # Application settings
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 25  # gpt-4o-transcribe-diarize limit is 25MB
    
    # Default language for transcription
    default_language: str = "nl"  # Dutch as default for Raad van State


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
