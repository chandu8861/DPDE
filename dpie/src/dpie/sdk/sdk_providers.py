"""DPIE Python SDK Provider Management

Provider management for the DPIE Python SDK.

Handles LLM provider configuration, API key management, and provider selection.
"""

from __future__ import annotations

from typing import Dict, Optional

from .sdk_core import logger

# Global provider state
_provider_config: Dict[str, str] = {}

# Set API key
def set_api_key(provider: str, api_key: str) -> None:
    """Set an API key for a specific provider.
    
    Args:
        provider: Provider name ("openai", "anthropic", "google_gemini", "ollama")
        api_key: The API key value
    """
    _provider_config[provider] = api_key
    logger.info(f"API key set for provider: {provider}")

# Get provider config
def get_api_key(provider: Optional[str] = None) -> Optional[str]:
    """Get an API key for a specific provider.
    
    Args:
        provider: Provider name (uses default if None)
        
    Returns:
        API key string or None
    """
    if provider:
        return _provider_config.get(provider)
    # Return first available
    for key in _provider_config.values():
        if key:
            return key
    return None

# Provider availability
def list_providers_status() -> Dict[str, bool]:
    """Check which providers have API keys configured.
    
    Returns:
        Dict mapping provider names to availability status
    """
    from .sdk_core import settings
    
    return {
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
        "google_gemini": bool(settings.google_api_key),
        "ollama": True,  # Ollama is local, always "available" if running
    }

# Export
__all__ = [
    "set_api_key",
    "get_api_key",
    "list_providers_status",
]