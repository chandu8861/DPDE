"""DPIE Agent Registry Module

Provides centralized registration, lookup, and lifecycle management for DPIE agents.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
import logging

from dpie.schemas import AgentType

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing DPIE specialized agents."""

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}
        self._enabled: Dict[str, bool] = {}

    def _key(self, agent_type: Union[AgentType, str]) -> str:
        if hasattr(agent_type, "value"):
            return str(agent_type.value)
        return str(agent_type)

    def register(self, agent: Any, enabled: bool = True) -> None:
        """Register an agent instance."""
        key = self._key(agent.agent_type)
        self._agents[key] = agent
        self._enabled[key] = enabled
        logger.debug(f"Registered agent: {key} (enabled={enabled})")

    def get(self, agent_type: Union[AgentType, str]) -> Optional[Any]:
        """Get an agent by its AgentType or string name."""
        return self._agents.get(self._key(agent_type))

    def get_agent(self, agent_type: Union[AgentType, str]) -> Optional[Any]:
        """Alias for get()."""
        return self.get(agent_type)

    def is_agent_enabled(self, agent_type: Union[AgentType, str]) -> bool:
        """Check if an agent is registered and enabled."""
        key = self._key(agent_type)
        if key not in self._agents:
            return False
        return self._enabled.get(key, True)

    def enable_agent(self, agent_type: Union[AgentType, str]) -> None:
        """Enable an agent."""
        key = self._key(agent_type)
        self._enabled[key] = True

    def disable_agent(self, agent_type: Union[AgentType, str]) -> None:
        """Disable an agent."""
        key = self._key(agent_type)
        self._enabled[key] = False

    def list_agents(self) -> List[Any]:
        """Return a list of all registered agents."""
        return list(self._agents.values())

    def get_all(self) -> Dict[str, Any]:
        """Return dict of all registered agents."""
        return dict(self._agents)

    def clear(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
        self._enabled.clear()

    # Dict-like compatibility
    def __getitem__(self, item: Union[AgentType, str]) -> Any:
        return self._agents[self._key(item)]

    def __setitem__(self, key: Union[AgentType, str], value: Any) -> None:
        self.register(value)

    def __contains__(self, item: Union[AgentType, str]) -> bool:
        return self._key(item) in self._agents

    def items(self):
        return self._agents.items()

    def keys(self):
        return self._agents.keys()

    def values(self):
        return self._agents.values()

    def __len__(self) -> int:
        return len(self._agents)


# Global singleton registry
_global_registry: AgentRegistry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry singleton."""
    return _global_registry


def init_agent_registry() -> AgentRegistry:
    """Reset and return the global agent registry."""
    global _global_registry
    _global_registry.clear()
    return _global_registry


def register_agent(agent: Any) -> None:
    """Register an agent in the global registry."""
    _global_registry.register(agent)


__all__ = [
    "AgentRegistry",
    "get_agent_registry",
    "init_agent_registry",
    "register_agent",
]

