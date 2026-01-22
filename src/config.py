"""Configuration settings for Sacrilege Engine."""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/sacrilege"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Demo Processing
    max_demo_size_mb: int = 500
    demo_upload_dir: Path = Path("/tmp/sacrilege/uploads")
    
    # Performance
    tick_sample_rate: int = 16  # Sample every N ticks
    visibility_cache_size: int = 10000
    
    # Analysis
    trade_window_perfect_ms: int = 1500
    trade_window_late_ms: int = 3000
    trade_max_distance: float = 800.0
    pre_aim_angle_threshold: float = 15.0
    
    model_config = SettingsConfigDict(
        env_prefix="SACRILEGE_",
        env_file=".env"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
