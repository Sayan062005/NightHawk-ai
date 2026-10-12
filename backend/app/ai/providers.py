"""NightHawk AI — AI Provider Layer.

Supports NVIDIA NIM, OpenAI-compatible, mock, and deterministic fallback.
All AI output is advisory — the backend validates everything independently.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AIResponse:
    """Structured response from an AI provider."""
    content: str = ""
    parsed: dict[str, Any] | None = None
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    success: bool = True
    error: str = ""
    is_fallback: bool = False


class AIProvider(ABC):
    """Base class for AI providers."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Generate a response from the AI model."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        ...


class NvidiaProvider(AIProvider):
    """NVIDIA NIM API provider (OpenAI-compatible)."""

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.nvidia_api_key
        self._base_url = settings.nvidia_base_url
        self._model = settings.nvidia_model
        self._timeout = settings.nvidia_timeout_seconds
        self._max_retries = settings.nvidia_max_retries

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        if not self._api_key or self._api_key.startswith("nvapi-PLACEHOLDER"):
            return AIResponse(success=False, error="NVIDIA API key not configured", provider="nvidia")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Candidate models to try in fallback order
        candidate_models = [self._model]
        if "glm-5.3" in self._model and not self._model.endswith("-flash"):
            candidate_models.append("z-ai/glm-5.3-flash")
        elif self._model != "z-ai/glm-5.3-flash":
            candidate_models.append("z-ai/glm-5.3-flash")

        start = time.monotonic()
        last_error = ""

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for model_candidate in candidate_models:
                payload: dict[str, Any] = {
                    "model": model_candidate,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if json_schema:
                    payload["response_format"] = {"type": "json_object"}

                for attempt in range(max(1, self._max_retries)):
                    try:
                        logger.info("nvidia_request_attempt", model=model_candidate, attempt=attempt + 1)
                        resp = await client.post(
                            f"{self._base_url}/chat/completions",
                            json=payload,
                            headers={
                                "Authorization": f"Bearer {self._api_key}",
                                "Content-Type": "application/json",
                            },
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            latency = int((time.monotonic() - start) * 1000)
                            msg = data["choices"][0]["message"]
                            # Handle reasoning models (GLM / DeepSeek) where thinking is in reasoning_content
                            content = msg.get("content") or msg.get("reasoning_content") or ""
                            usage = data.get("usage", {})

                            parsed = None
                            if json_schema:
                                try:
                                    parsed = json.loads(content)
                                except json.JSONDecodeError:
                                    logger.warning("ai_json_parse_failed", content=content[:200])

                            return AIResponse(
                                content=content,
                                parsed=parsed,
                                model=model_candidate,
                                provider="nvidia",
                                prompt_tokens=usage.get("prompt_tokens", 0),
                                completion_tokens=usage.get("completion_tokens", 0),
                                total_tokens=usage.get("total_tokens", 0),
                                latency_ms=latency,
                                is_fallback=(model_candidate != self._model),
                            )
                        else:
                            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                            logger.warning("nvidia_api_error_response", status=resp.status_code, model=model_candidate)
                    except Exception as exc:
                        last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
                        logger.warning("nvidia_api_attempt_failed", error=last_error, model=model_candidate)

                    # Short backoff before retry or fallback
                    await asyncio.sleep(1.0)

        latency = int((time.monotonic() - start) * 1000)
        return AIResponse(
            success=False,
            error=last_error or "All NVIDIA model attempts timed out or failed",
            provider="nvidia",
            latency_ms=latency,
            model=self._model,
        )

    async def health_check(self) -> bool:
        if not self._api_key or self._api_key.startswith("nvapi-PLACEHOLDER"):
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def provider_name(self) -> str:
        return "nvidia"


class OpenAICompatProvider(AIProvider):
    """OpenAI-compatible API provider."""

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url
        self._model = settings.openai_model
        self._timeout = settings.nvidia_timeout_seconds

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        if not self._api_key or self._api_key.startswith("sk-PLACEHOLDER"):
            return AIResponse(success=False, error="OpenAI API key not configured", provider="openai")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_schema:
            payload["response_format"] = {"type": "json_object"}

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            latency = int((time.monotonic() - start) * 1000)
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            parsed = None
            if json_schema:
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    pass

            return AIResponse(
                content=content,
                parsed=parsed,
                model=self._model,
                provider="openai",
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_ms=latency,
            )
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return AIResponse(
                success=False,
                error=f"{type(e).__name__}: {str(e)[:200]}",
                provider="openai",
                latency_ms=latency,
                model=self._model,
            )

    async def health_check(self) -> bool:
        if not self._api_key or self._api_key.startswith("sk-PLACEHOLDER"):
            return False
        return True

    def provider_name(self) -> str:
        return "openai"


class MockProvider(AIProvider):
    """Mock AI provider for testing."""

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        mock_response = {
            "analysis": "Mock analysis for testing",
            "recommendations": ["This is a mock recommendation"],
            "next_task": None,
            "confidence": 0.5,
        }
        return AIResponse(
            content=json.dumps(mock_response),
            parsed=mock_response,
            model="mock",
            provider="mock",
            prompt_tokens=len(system_prompt.split()),
            completion_tokens=20,
            total_tokens=len(system_prompt.split()) + 20,
            latency_ms=1,
        )

    async def health_check(self) -> bool:
        return True

    def provider_name(self) -> str:
        return "mock"


class FallbackProvider(AIProvider):
    """Deterministic rule-based fallback when no AI provider is available."""

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        # Simple rule-based responses
        response = {
            "analysis": "AI unavailable — using rule-based analysis. "
                       "Review findings manually and prioritize by severity.",
            "recommendations": [
                "Review all critical and high severity findings first",
                "Verify candidate findings with manual testing",
                "Check for false positives before reporting",
            ],
            "next_task": None,
            "confidence": 0.3,
        }
        return AIResponse(
            content=json.dumps(response),
            parsed=response,
            model="fallback",
            provider="fallback",
            is_fallback=True,
        )

    async def health_check(self) -> bool:
        return True  # Always available

    def provider_name(self) -> str:
        return "fallback"


class AIProviderManager:
    """Manages AI providers with automatic fallback."""

    def __init__(self):
        settings = get_settings()
        self._providers: dict[str, AIProvider] = {
            "nvidia": NvidiaProvider(),
            "openai": OpenAICompatProvider(),
            "mock": MockProvider(),
            "fallback": FallbackProvider(),
        }
        self._primary = settings.ai_provider
        self._fallback = FallbackProvider()

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Generate a response, falling back if primary fails."""
        # Try primary provider
        provider = self._providers.get(self._primary, self._fallback)
        response = await provider.generate(
            system_prompt, user_prompt, json_schema, temperature, max_tokens
        )

        if response.success:
            return response

        # Try fallback
        logger.warning(
            "ai_primary_failed_using_fallback",
            primary=self._primary,
            error=response.error,
        )
        return await self._fallback.generate(
            system_prompt, user_prompt, json_schema, temperature, max_tokens
        )

    async def health_check(self) -> tuple[bool, str]:
        """Check primary provider health."""
        provider = self._providers.get(self._primary, self._fallback)
        healthy = await provider.health_check()
        return healthy, provider.provider_name()

    @property
    def primary_provider(self) -> str:
        return self._primary


_manager: AIProviderManager | None = None


def get_ai_manager() -> AIProviderManager:
    """Get or create the AI provider manager singleton."""
    global _manager
    if _manager is None:
        _manager = AIProviderManager()
    return _manager
