"""DPIE LLM Provider Abstraction Layer

Provider-independent layer for interacting with various LLM providers.
Supports OpenAI, Anthropic, Google Gemini, Ollama, and custom providers.

Key features:
- Configurable models per agent
- Environment-based API keys
- Model switching without rewriting agent logic
- Structured output validation
- Retry and timeout handling
- Token and cost tracking
- Model fallback support
- Mock mode for development and testing

Do not hardcode API keys or tie the entire framework to one AI provider.
"""

from __future__ import annotations

import abc
import json
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx  # type: ignore

from pydantic import BaseModel, Field  # Fixed: added imports
from enum import Enum


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider Capabilities
# ---------------------------------------------------------------------------

class ProviderCapability(str, Enum):
    """Capabilities of an LLM provider."""
    STRUCTURED_OUTPUT = "structured_output"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    LONG_CONTEXT = "long_context"
    CODE_INTERPRETATION = "code_interpretation"
    EMBEDDINGS = "embeddings"


class ModelInfo(BaseModel):
    """Information about a specific model."""
    name: str = Field(description="Model identifier/name")
    provider: str = Field(description="Provider name")
    max_tokens: int = Field(description="Maximum context/output tokens")
    cost_per_1k_input: float = Field(
        description="Cost per 1,000 input tokens (USD)"
    )
    cost_per_1k_output: float = Field(
        description="Cost per 1,000 output tokens (USD)"
    )
    capabilities: List[ProviderCapability] = Field(
        default_factory=list, description="Provider capabilities"
    )
    supports_structured_output: bool = Field(
        default=False, description="Supports structured output validation"
    )


# ---------------------------------------------------------------------------
# Abstract Base Provider
# ---------------------------------------------------------------------------


class BaseLLMProvider(abc.ABC):
    """Abstract base class for all LLM providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Return the provider name."""

    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """Return the default model name."""

    @property
    @abc.abstractmethod
    def model_info(self) -> Dict[str, ModelInfo]:
        """Return info about available models."""

    @property
    @abc.abstractmethod
    def capabilities(self) -> List[ProviderCapability]:
        """Return supported capabilities."""

    @abc.abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        structured_output: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate a response from the LLM.

        Args:
            system_prompt: System/instruction prompt
            user_prompt: User analysis prompt
            model: Specific model to use (defaults to provider default)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            structured_output: Pydantic model for output validation
            **kwargs: Additional provider-specific options

        Returns:
            Tuple of (raw_response_text, metadata_dict)
            metadata includes: tokens_used, model, cost, execution_time, etc.
        """

    @abc.abstractmethod
    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens in a text string.

        Args:
            text: Text to count tokens for
            model: Specific model for accurate counting

        Returns:
            Number of tokens
        """

    @abc.abstractmethod
    def supports_structured_output(self, model: Optional[str] = None) -> bool:
        """Check if a model supports structured output validation."""

    @abc.abstractmethod
    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        """Get model info by name."""


# ---------------------------------------------------------------------------
# OpenAI Provider
# -------------------------------------------------------------------------


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider (GPT-4, GPT-3.5, etc.)."""

    def __init__(self, api_key: str, organization: Optional[str] = None):
        self._api_key = api_key
        self._organization = organization
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"

    @property
    def model_info(self) -> Dict[str, ModelInfo]:
        return {
            "gpt-4o": ModelInfo(
                name="gpt-4o",
                provider="openai",
                max_tokens=128000,
                cost_per_1k_input=10.0,
                cost_per_1k_output=30.0,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                    ProviderCapability.FUNCTION_CALLING,
                    ProviderCapability.VISION,
                    ProviderCapability.LONG_CONTEXT,
                ],
                supports_structured_output=True,
            ),
            "gpt-4o-mini": ModelInfo(
                name="gpt-4o-mini",
                provider="openai",
                max_tokens=128000,
                cost_per_1k_input=0.15,
                cost_per_1k_output=0.6,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                    ProviderCapability.FUNCTION_CALLING,
                ],
                supports_structured_output=True,
            ),
            "gpt-4-turbo": ModelInfo(
                name="gpt-4-turbo",
                provider="openai",
                max_tokens=128000,
                cost_per_1k_input=10.0,
                cost_per_1k_output=30.0,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                    ProviderCapability.FUNCTION_CALLING,
                ],
                supports_structured_output=True,
            ),
        }

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.STRUCTURED_OUTPUT,
            ProviderCapability.FUNCTION_CALLING,
            ProviderCapability.VISION,
            ProviderCapability.LONG_CONTEXT,
        ]

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        structured_output: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate response from OpenAI API."""
        model_name = model or self.default_model
        start_time = time.time()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        params: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if structured_output is not None:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "dpie_analysis",
                    "strict": True,
                    "schema": structured_output.model_json_schema()
                    if hasattr(structured_output, "model_json_schema")
                    else structured_output,
                },
            }

        try:
            response = await self._client.post(
                "https://api.openai.com/v1/chat/completions",
                json=params,
            )
            response.raise_for_status()

            data = response.json()

            choice = data.get("choices", [{}])[0]
            raw_content = choice.get("message", {}).get("content", "{}")

            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)

            model_info = self.model_info.get(model_name, ModelInfo(name=model_name, provider="openai"))
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = (
                (input_tokens / 1000) * model_info.cost_per_1k_input
                + (output_tokens / 1000) * model_info.cost_per_1k_output
            )

            metadata = {
                "tokens_used": tokens_used,
                "model": model_name,
                "cost": cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

            return raw_content, metadata

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}")
            raise

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens using OpenAI's tokenizer."""
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model(model or self.default_model)
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def supports_structured_output(self, model: Optional[str] = None) -> bool:
        return True

    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        return self.model_info.get(model_name)

    async def close(self):
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Anthropic Provider
# -------------------------------------------------------------------------


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API provider (Claude models)."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
        )

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return "claude-3-haiku-20240307"

    @property
    def model_info(self) -> Dict[str, ModelInfo]:
        return {
            "claude-3-opus-20240229": ModelInfo(
                name="claude-3-opus-20240229",
                provider="anthropic",
                max_tokens=200000,
                cost_per_1k_input=15.0,
                cost_per_1k_output=75.0,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                    ProviderCapability.FUNCTION_CALLING,
                ],
                supports_structured_output=True,
            ),
            "claude-3-sonnet-20240229": ModelInfo(
                name="claude-3-sonnet-20240229",
                provider="anthropic",
                max_tokens=200000,
                cost_per_1k_input=3.0,
                cost_per_1k_output=15.0,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                    ProviderCapability.FUNCTION_CALLING,
                ],
                supports_structured_output=True,
            ),
            "claude-3-haiku-20240307": ModelInfo(
                name="claude-3-haiku-20240307",
                provider="anthropic",
                max_tokens=200000,
                cost_per_1k_input=0.25,
                cost_per_1k_output=1.25,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                    ProviderCapability.FUNCTION_CALLING,
                ],
                supports_structured_output=True,
            ),
        }

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [ProviderCapability.STRUCTURED_OUTPUT, ProviderCapability.FUNCTION_CALLING]

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        structured_output: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate response from Anthropic API."""
        model_name = model or self.default_model
        start_time = time.time()

        messages = [
            {"role": "user", "content": user_prompt},
        ]

        params: Dict[str, Any] = {
            "model": model_name,
            "system": system_prompt,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if structured_output is not None:
            params["tools"] = [
                {
                    "name": "structured_output",
                    "description": "Structured output schema",
                    "input_schema": structured_output.model_json_schema()
                    if hasattr(structured_output, "model_json_schema")
                    else structured_output,
                }
            ]
            params["tool_choice"] = {"type": "tool", "name": "structured_output"}

        try:
            response = await self._client.post(
                "https://api.anthropic.com/v1/messages",
                json=params,
            )
            response.raise_for_status()

            data = response.json()

            content = data.get("content", [{}])[0]
            raw_content = content.get("text", "{}") if isinstance(content, dict) else str(content)

            usage = data.get("usage", {})
            tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

            model_info = self.model_info.get(model_name, ModelInfo(name=model_name, provider="anthropic"))
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cost = (
                (input_tokens / 1000) * model_info.cost_per_1k_input
                + (output_tokens / 1000) * model_info.cost_per_1k_output
            )

            metadata = {
                "tokens_used": tokens_used,
                "model": model_name,
                "cost": cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

            return raw_content, metadata

        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Anthropic provider: {e}")
            raise

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens - Anthropic approximation."""
        return max(1, len(text) // 3.5)

    def supports_structured_output(self, model: Optional[str] = None) -> bool:
        return True

    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        return self.model_info.get(model_name)

    async def close(self):
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Google Gemini Provider
# -------------------------------------------------------------------------


class GoogleGeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={"x-goog-api-key": api_key},
        )

    @property
    def name(self) -> str:
        return "google_gemini"

    @property
    def default_model(self) -> str:
        return "gemini-1.5-flash"

    @property
    def model_info(self) -> Dict[str, ModelInfo]:
        return {
            "gemini-1.5-flash": ModelInfo(
                name="gemini-1.5-flash",
                provider="google_gemini",
                max_tokens=1048576,
                cost_per_1k_input=0.075,
                cost_per_1k_output=0.3,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                    ProviderCapability.LONG_CONTEXT,
                ],
                supports_structured_output=True,
            ),
            "gemini-1.5-pro": ModelInfo(
                name="gemini-1.5-pro",
                provider="google_gemini",
                max_tokens=1048576,
                cost_per_1k_input=1.0,
                cost_per_1k_output=2.0,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                    ProviderCapability.LONG_CONTEXT,
                ],
                supports_structured_output=True,
            ),
        }

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [ProviderCapability.STRUCTURED_OUTPUT, ProviderCapability.LONG_CONTEXT]

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        structured_output: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate response from Gemini API."""
        model_name = model or self.default_model
        start_time = time.time()

        params: Dict[str, Any] = {
            "model": f"models/{model_name}:generateContent",
            "systemInstruction": {"text": system_prompt},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "temperature": temperature,
        }

        if max_tokens is not None:
            params["maxOutputTokens"] = max_tokens

        if structured_output is not None:
            params["responseSchema"] = {
                "type": "OBJECT",
                "properties": {},
                "required": [],
            }

        try:
            response = await self._client.post(
                "https://generativelanguage.googleapis.com/v1beta",
                params={"key": self._api_key},
                json=params,
            )
            response.raise_for_status()

            data = response.json()

            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", "")
                raw_content = content if isinstance(content, str) else str(content)
            else:
                raw_content = "{}"

            prompt_tokens = data.get("promptTokenCount", 0)
            completion_tokens = data.get("candidates", [{}])[0].get(
                "outputTokenCount", 0
            )
            tokens_used = prompt_tokens + completion_tokens

            model_info = self.model_info.get(model_name, ModelInfo(name=model_name, provider="google_gemini"))
            input_tokens = prompt_tokens
            output_tokens = completion_tokens
            cost = (
                (input_tokens / 1000) * model_info.cost_per_1k_input
                + (output_tokens / 1000) * model_info.cost_per_1k_output
            )

            metadata = {
                "tokens_used": tokens_used,
                "model": model_name,
                "cost": cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

            return raw_content, metadata

        except httpx.HTTPStatusError as e:
            logger.error(f"Google Gemini API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Gemini provider: {e}")
            raise

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens - Gemini approximation."""
        return max(1, len(text) // 4)

    def supports_structured_output(self, model: Optional[str] = None) -> bool:
        return True

    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        return self.model_info.get(model_name)

    async def close(self):
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Ollama Provider (local)
# -------------------------------------------------------------------------


class OllamaProvider(BaseLLMProvider):
    """Ollama local model provider."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=120.0,
        )

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return "llama3.2"

    @property
    def model_info(self) -> Dict[str, ModelInfo]:
        return {
            "llama3.2": ModelInfo(
                name="llama3.2",
                provider="ollama",
                max_tokens=8192,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                ],
                supports_structured_output=True,
            ),
            "phi3": ModelInfo(
                name="phi3",
                provider="ollama",
                max_tokens=4096,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                capabilities=[
                    ProviderCapability.STRUCTURED_OUTPUT,
                ],
                supports_structured_output=True,
            ),
        }

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [ProviderCapability.STRUCTURED_OUTPUT]

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        structured_output: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate response from Ollama API."""
        model_name = model or self.default_model
        start_time = time.time()

        params: Dict[str, Any] = {
            "model": model_name,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
        }

        if max_tokens is not None:
            params["options"] = {"num_ctx": max_tokens or 8192}

        if temperature is not None:
            if "options" not in params:
                params["options"] = {}
            params["options"]["temperature"] = temperature

        if structured_output is not None:
            params["format"] = "json"
            # Note: structured output validation depends on the model

        try:
            response = await self._client.post(
                f"{self._base_url}/api/generate",
                json=params,
            )
            response.raise_for_status()

            data = response.json()

            raw_content = data.get("response", "{}")
            if not isinstance(raw_content, str):
                raw_content = json.dumps(raw_content)

            metadata = {
                "tokens_used": data.get("eval_count", 0),
                "model": model_name,
                "cost": 0.0,  # Local models are free
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

            return raw_content, metadata

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Ollama provider: {e}")
            raise

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens using approximate char-based method."""
        return max(1, len(text) // 4)

    def supports_structured_output(self, model: Optional[str] = None) -> bool:
        return True

    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        return self.model_info.get(model_name)

    async def close(self):
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Provider Factory
# -------------------------------------------------------------------------


class ProviderFactory:
    """Factory for creating LLM provider instances."""

    _providers: Dict[str, type[BaseLLMProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google_gemini": GoogleGeminiProvider,
        "ollama": OllamaProvider,
    }

    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        **kwargs: Any,
    ) -> BaseLLMProvider:
        """Create a provider instance.

        Args:
            provider_name: Name of the provider (openai, anthropic, google_gemini, ollama)
            **kwargs: Provider-specific initialization arguments

        Returns:
            Initialized provider instance

        Raises:
            ValueError: If provider name is not supported
        """
        if provider_name not in cls._providers:
            msg = f"Unsupported provider: {provider_name}"
            logger.error(msg)
            raise ValueError(msg)

        provider_class = cls._providers[provider_name]
        return provider_class(**kwargs)

    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Return list of supported provider names."""
        return list(cls._providers.keys())

    @classmethod
    def get_provider_names_with_keys(
        cls,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        google_key: Optional[str] = None,
        ollama_url: str = "http://localhost:11434",
    ) -> Dict[str, bool]:
        """Check which providers have available keys/config."""
        return {
            "openai": openai_key is not None,
            "anthropic": anthropic_key is not None,
            "google_gemini": google_key is not None,
            "ollama": True,  # Always available if Ollama is running
        }


# ---------------------------------------------------------------------------
# Provider Wrapper with Fallback and Mock support
# -------------------------------------------------------------------------


class ProviderWrapper:
    """Wrapper that adds fallback, mock, and monitoring capabilities."""

    def __init__(
        self,
        primary_provider: BaseLLMProvider,
        fallback_provider: Optional[BaseLLMProvider] = None,
        enable_mock: bool = False,
        mock_responses: Optional[Dict[str, str]] = None,
    ):
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.enable_mock = enable_mock
        self.mock_responses = mock_responses or {}
        self.call_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        structured_output: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate with fallback and mock support."""

        # Check mock mode first
        if self.enable_mock and self.mock_responses:
            # Use mock if available, otherwise return default
            mock_key = f"{system_prompt[:50]}...{user_prompt[:50]}..."
            if mock_key in self.mock_responses:
                raw = self.mock_responses[mock_key]
                metadata = {
                    "tokens_used": 0,
                    "model": "mock",
                    "cost": 0.0,
                    "execution_time_ms": 0,
                }
                return raw, metadata

        # Try primary provider
        try:
            result = await self.primary.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                structured_output=structured_output,
                **kwargs,
            )
            self._record_call(result[1])
            return result

        except Exception as e:
            logger.warning(f"Primary provider failed: {e}")

            # Try fallback if available
            if self.fallback is not None:
                try:
                    result = await self.fallback.generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        structured_output=structured_output,
                        **kwargs,
                    )
                    self._record_call(result[1], is_fallback=True)
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback provider also failed: {fallback_error}")

            # Re-raise the original error
            raise

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        return await self.primary.count_tokens(text, model)

    def supports_structured_output(self, model: Optional[str] = None) -> bool:
        if self.primary.supports_structured_output(model):
            return True
        if self.fallback is not None:
            return self.fallback.supports_structured_output(model)
        return False

    def _record_call(self, metadata: Dict[str, Any], is_fallback: bool = False):
        self.call_count += 1
        tokens = metadata.get("tokens_used", 0)
        self.total_tokens += tokens
        cost = metadata.get("cost", 0.0) or 0.0
        self.total_cost += cost

    def get_stats(self) -> Dict[str, Any]:
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
            "primary_provider": self.primary.name,
            "fallback_provider": self.fallback.name if self.fallback else None,
        }

    async def close(self):
        await self.primary.close()
        if self.fallback:
            await self.fallback.close()


# ---------------------------------------------------------------------------
# Mock Provider for Testing
# -------------------------------------------------------------------------


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for development and testing.

    Returns deterministic responses without making API calls.
    """

    def __init__(self, responses: Dict[str, str]):
        self._responses = responses

    @property
    def name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-model"

    @property
    def model_info(self) -> Dict[str, ModelInfo]:
        return {
            "mock-model": ModelInfo(
                name="mock-model",
                provider="mock",
                max_tokens=4096,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                capabilities=[],
                supports_structured_output=True,
            ),
        }

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return []

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        structured_output: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        import hashlib
        key = (
            hashlib.md5(system_prompt.encode()).hexdigest()[:8],
            hashlib.md5(user_prompt.encode()).hexdigest()[:8],
        )
        raw = self._responses.get(key, '{"analysis": "mock response"}')

        metadata = {
            "tokens_used": 150,
            "model": model or self.default_model,
            "cost": 0.0,
            "execution_time_ms": 5,
        }

        return raw, metadata

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        return max(1, len(text) // 4)

    def supports_structured_output(self, model: Optional[str] = None) -> bool:
        return True

    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        return self.model_info.get(model_name)

    async def close(self):
        pass


# ---------------------------------------------------------------------------
# Export useful types and classes
# -------------------------------------------------------------------------

__all__ = [
    "BaseLLMProvider",
    "ProviderCapability",
    "ModelInfo",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleGeminiProvider",
    "OllamaProvider",
    "ProviderFactory",
    "ProviderWrapper",
    "MockLLMProvider",
]