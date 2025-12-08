"""
Jarvis Web Agent - Configuration
Pydantic settings for environment-based configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Core services
    REDIS_URL: str = "redis://localhost:6379"
    FLARESOLVERR_URL: str = "http://localhost:8191"
    
    # Proxy configuration
    HOME_PROXY_ENABLED: bool = True
    HOME_PROXY_URL: Optional[str] = None
    SACVPN_NODES: Optional[str] = None  # Comma-separated list
    
    # Browser settings
    MAX_CONCURRENT_BROWSERS: int = 3
    BROWSER_TIMEOUT: int = 30000
    HEADLESS: bool = True
    
    # Security
    API_KEY: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # CAPTCHA
    WHISPER_MODEL: str = "base"
    
    # Jarvis Core connection
    JARVIS_CORE_URL: Optional[str] = None
    
    @property
    def sacvpn_node_list(self) -> List[str]:
        """Parse SACVPN nodes from comma-separated string"""
        if not self.SACVPN_NODES:
            return []
        return [node.strip() for node in self.SACVPN_NODES.split(",") if node.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
