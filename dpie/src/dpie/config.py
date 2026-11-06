"""DPIE Configuration Module

Central configuration for the DPIE framework, including:
- AI model provider settings
- Agent execution modes
- Detection thresholds
- API settings
- Paths and directories
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional


class Settings(BaseModel):
    """Main application settings."""
    
    # Environment
    environment: str = Field(default="development", description="Application environment")
    
    # AI Model Provider Settings
    default_provider: str = Field(default="openai", description="Default LLM provider")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    google_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server base URL")
    
    # Execution Modes
    default_mode: Literal["fast", "deep", "full"] = Field(
        default="fast", description="Default orchestration mode"
    )
    
    # Detection thresholds
    default_confidence_threshold: float = Field(
        default=0.5, description="Default confidence threshold for detections"
    )
    
    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    
    # Model Fallback
    enable_model_fallback: bool = Field(
        default=True, description="Enable model fallback on errors"
    )
    fallback_provider: Optional[str] = Field(
        default=None, description="Fallback provider on primary failure"
    )
    
    # Security
    rate_limit_per_minute: int = Field(
        default=100, description="Default rate limit per minute"
    )
    
    # Knowledge base / runtime
    kb_max_evidence: int = Field(default=5000, description="Max evidence records kept in memory (0=unbounded)")
    kb_max_history: int = Field(default=2000, description="Max investigation/execution log entries kept in memory (0=unbounded)")
    kb_batch_commits: bool = Field(default=True, description="Batch SQLite commits for write bursts")
    api_enable_dashboard: bool = Field(default=True, description="Serve /dashboard")
    provider_max_retries: int = Field(default=2, ge=0, le=5, description="Max LLM provider retries for transient errors")
    provider_retry_backoff_s: float = Field(default=0.5, ge=0.0, le=10.0, description="Base backoff seconds between retries")
    
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)


# Global settings instance
settings = Settings()


def load_settings() -> Settings:
    """Load settings from environment variables or config file.
    
    Returns:
        Configured Settings instance
    """
    import os
    
    # Override from environment variables if present
    if env_val := os.getenv("DPIE_ENVIRONMENT"):
        settings.environment = env_val
    if env_val := os.getenv("DPIE_DEFAULT_PROVIDER"):
        settings.default_provider = env_val
    if env_val := os.getenv("DPIE_DEFAULT_MODE"):
        settings.default_mode = env_val
    if env_val := os.getenv("DPIE_CONFIDENCE_THRESHOLD"):
        settings.default_confidence_threshold = float(env_val)
    if env_val := os.getenv("DPIE_API_PORT"):
        settings.api_port = int(env_val)
    if env_val := os.getenv("DPIE_DASHBOARD_PORT"):
        settings.dashboard_port = int(env_val)
    if env_val := os.getenv("DPIE_ENABLE_FALLBACK"):
        settings.enable_model_fallback = env_val.lower() == "true"
    if env_val := os.getenv("DPIE_RATE_LIMIT"):
        settings.rate_limit_per_minute = int(env_val)
    
    # API keys from standard or DPIE-specific env vars
    if env_val := os.getenv("DPIE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"):
        settings.openai_api_key = env_val
    if env_val := os.getenv("DPIE_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY"):
        settings.anthropic_api_key = env_val
    if env_val := os.getenv("DPIE_GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        settings.google_api_key = env_val
    if env_val := os.getenv("DPIE_OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL"):
        settings.ollama_base_url = env_val

    return settings


def reload_settings() -> Settings:
    """Reload settings, overwriting with environment defaults."""
    return load_settings()