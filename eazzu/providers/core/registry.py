"""Provider registry — allows unlimited provider registration by name."""
from __future__ import annotations

from typing import Type
from eazzu.providers.core.base_provider import BaseProvider

PROVIDER_REGISTRY: dict[str, Type[BaseProvider]] = {}


def register_provider(cls: Type[BaseProvider]) -> Type[BaseProvider]:
    """Class decorator to register a provider by its .name attribute."""
    if not getattr(cls, "name", None):
        raise ValueError(f"Provider {cls.__name__} missing 'name' attribute")
    PROVIDER_REGISTRY[cls.name.lower()] = cls
    return cls


def list_providers(category: str | None = None) -> list[str]:
    if category is None:
        return sorted(PROVIDER_REGISTRY.keys())
    return sorted(
        n for n, c in PROVIDER_REGISTRY.items() if getattr(c, "category", "llm") == category
    )


def get_provider(name: str) -> Type[BaseProvider]:
    key = name.lower().strip()
    if key not in PROVIDER_REGISTRY:
        raise KeyError(
            f"Unknown provider '{name}'. Available: {', '.join(list_providers())}"
        )
    return PROVIDER_REGISTRY[key]
