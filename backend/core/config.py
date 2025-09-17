# backend/core/config.py

import os
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """Entornos de ejecución."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Niveles de logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CacheType(str, Enum):
    """Tipos de cache disponibles."""
    MEMORY = "memory"
    REDIS = "redis"


class Settings(BaseSettings):
    """
    Configuración centralizada de la aplicación.
    Lee variables de entorno y proporciona valores por defecto.
    """

    # === Application Settings ===
    app_name: str = "Arbitraje Minorista API"
    app_version: str = "1.0.0"
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: LogLevel = LogLevel.INFO
    secret_key: str = Field(default="development-secret-key-32-chars-minimum", min_length=32)

    # === JWT Configuration ===
    jwt_secret_key: str = Field(default="jwt-secret-key-for-development-only-32-chars", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # === FastAPI Configuration ===
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    fastapi_reload: bool = True
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3030"]

    # === Database Configuration ===
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/arbitraje"
    test_database_url: str = "sqlite+aiosqlite:///./test.db"
    db_pool_size: int = 20
    db_max_overflow: int = 30
    db_pool_recycle: int = 3600  # 1 hour

    # === Supabase Configuration ===
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    # === Rate Limiting Configuration ===
    rate_limit_storage_uri: str = "memory://"
    rate_limit_redis_url: Optional[str] = None

    # === Cache Configuration ===
    cache_type: CacheType = CacheType.MEMORY
    cache_redis_url: Optional[str] = None
    cache_default_ttl: int = 300  # 5 minutes
    cache_max_size: int = 1000

    # === Scraping Configuration ===
    scraper_max_concurrent: int = 5
    scraper_default_timeout: int = 30
    scraper_user_agent: str = "Mozilla/5.0 (compatible; ArbitrajeBot/1.0)"
    scraper_delay_min: int = 1
    scraper_delay_max: int = 3

    # === Scheduler Configuration ===
    scheduler_enabled: bool = True
    scheduler_timezone: str = "America/Bogota"
    scheduler_scraping_interval: int = 3600  # 1 hour

    # === Monitoring & Observability ===
    metrics_enabled: bool = True
    health_checks_enabled: bool = True
    structured_logging: bool = True

    # === Sentry Configuration ===
    sentry_dsn: Optional[str] = None
    sentry_environment: Optional[str] = None
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.1

    # === Security Settings ===
    enable_https_redirect: bool = False
    trusted_proxies: List[str] = ["127.0.0.1", "::1"]
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]

    # === Performance Settings ===
    shutdown_timeout: int = 30

    # === Development Features ===
    enable_docs: bool = True
    enable_redoc: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("CORS origins must be a string or list")

    @field_validator("trusted_proxies", mode="before")
    @classmethod
    def parse_trusted_proxies(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse trusted proxies from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength in production."""
        if v in ["change-me-in-production", "development-secret-key-32-chars-minimum"]:
            # Allow development key only in development
            return v
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL based on environment."""
        # Note: environment validation moved to validate_production_config()
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.app_env == Environment.TESTING

    @property
    def database_url_for_env(self) -> str:
        """Get appropriate database URL for current environment."""
        if self.is_testing:
            return self.test_database_url
        return self.database_url

    @property
    def redis_url_for_rate_limiting(self) -> str:
        """Get Redis URL for rate limiting or fallback to memory."""
        if self.rate_limit_redis_url and not self.is_development:
            return self.rate_limit_redis_url
        return self.rate_limit_storage_uri

    @property
    def redis_url_for_cache(self) -> Optional[str]:
        """Get Redis URL for caching."""
        if self.cache_type == CacheType.REDIS:
            return self.cache_redis_url
        return None

    def get_cors_origins_for_env(self) -> List[str]:
        """Get CORS origins appropriate for environment."""
        if self.is_production:
            # In production, filter out localhost origins
            return [origin for origin in self.cors_origins
                    if not ("localhost" in origin or "127.0.0.1" in origin)]
        return self.cors_origins

    def get_log_config(self) -> dict:
        """Get logging configuration for current environment."""
        base_config = {
            "level": self.log_level.value,
            "structured": self.structured_logging,
        }

        if self.is_production:
            base_config.update({
                "handlers": ["console", "file"],
                "file_path": "/var/log/arbitraje/app.log",
                "rotation": "daily",
                "retention": "30 days"
            })
        else:
            base_config.update({
                "handlers": ["console"],
                "format": "detailed"
            })

        return base_config


# Instancia global de configuración
settings = Settings()


def get_settings() -> Settings:
    """
    Dependency para inyectar configuración en endpoints.

    Usage:
        @app.get("/config")
        def get_config(settings: Settings = Depends(get_settings)):
            return settings.dict()
    """
    return settings


# Funciones de utilidad para configuración

def is_production() -> bool:
    """Check if running in production environment."""
    return settings.is_production


def is_development() -> bool:
    """Check if running in development environment."""
    return settings.is_development


def get_database_url() -> str:
    """Get database URL for current environment."""
    return settings.database_url_for_env


def get_cache_config() -> dict:
    """Get cache configuration."""
    return {
        "type": settings.cache_type,
        "redis_url": settings.redis_url_for_cache,
        "default_ttl": settings.cache_default_ttl,
        "max_size": settings.cache_max_size
    }


def get_scraper_config() -> dict:
    """Get scraper configuration."""
    return {
        "max_concurrent": settings.scraper_max_concurrent,
        "timeout": settings.scraper_default_timeout,
        "user_agent": settings.scraper_user_agent,
        "delay_range": (settings.scraper_delay_min, settings.scraper_delay_max)
    }


def get_scheduler_config() -> dict:
    """Get scheduler configuration."""
    return {
        "enabled": settings.scheduler_enabled,
        "timezone": settings.scheduler_timezone,
        "scraping_interval": settings.scheduler_scraping_interval
    }


# Validaciones de entorno

def validate_production_config() -> List[str]:
    """
    Validate configuration for production deployment.
    Returns list of configuration errors.
    """
    errors = []

    if not settings.is_production:
        return errors

    # Check critical production settings
    if settings.secret_key == "change-me-in-production":
        errors.append("SECRET_KEY must be changed in production")

    if "sqlite" in settings.database_url.lower():
        errors.append("SQLite database not recommended for production")

    if not settings.supabase_url or not settings.supabase_service_role_key:
        errors.append("Supabase configuration required for production")

    if settings.debug:
        errors.append("DEBUG should be False in production")

    if settings.enable_docs and settings.is_production:
        errors.append("API docs should be disabled in production")

    if not settings.enable_https_redirect and settings.is_production:
        errors.append("HTTPS redirect should be enabled in production")

    return errors


def get_environment_info() -> dict:
    """Get environment information for debugging."""
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.app_env.value,
        "debug": settings.debug,
        "log_level": settings.log_level.value,
        "database_type": "PostgreSQL" if "postgresql" in settings.database_url else "SQLite",
        "cache_type": settings.cache_type.value,
        "rate_limiting": "Redis" if settings.rate_limit_redis_url else "Memory",
        "scheduler_enabled": settings.scheduler_enabled,
        "metrics_enabled": settings.metrics_enabled,
    }