"""NightHawk AI — Base Agent Class.

All AI agents inherit from BaseAgent. Agents operate with:
- Strict token budgets
- Structured JSON output schemas
- Transparent prompt construction
- Fallback to deterministic rules if AI providers are unreachable
"""

from __future__ import annotations

import abc
import json
from typing import Any

from app.ai.providers import get_ai_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(abc.ABC):
    """Abstract base class for all NightHawk AI agents."""

    def __init__(self, name: str, role: str, max_tokens: int = 4000):
        self.name = name
        self.role = role
        self.max_tokens = max_tokens
        self.ai_manager = get_ai_manager()

    @abc.abstractmethod
    def get_system_prompt(self) -> str:
        """Return the agent's core system prompt."""
        raise NotImplementedError

    async def execute(self, user_prompt: str, schema: type | None = None) -> dict[str, Any]:
        """Execute reasoning cycle via AI provider with token tracking and fallback."""
        system_prompt = self.get_system_prompt()
        logger.info("agent_executing", agent=self.name, role=self.role)

        try:
            response = await self.ai_manager.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=self.max_tokens,
                temperature=0.2,
                schema=schema,
            )
            return {
                "success": True,
                "agent": self.name,
                "provider": response.get("provider", "unknown"),
                "content": response.get("content", ""),
                "structured": response.get("structured"),
                "tokens_used": response.get("tokens_used", 0),
            }
        except Exception as exc:
            logger.error("agent_execution_failed", agent=self.name, error=str(exc))
            return {
                "success": False,
                "agent": self.name,
                "error": str(exc),
                "content": f"Deterministic fallback: Agent {self.name} encountered an error.",
            }
