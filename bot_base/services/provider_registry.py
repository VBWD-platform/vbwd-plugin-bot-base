"""MessengerProviderRegistry — the Open/Closed extension point for adapters.

Adapters self-register their :class:`IMessengerProvider` on enable; the
outbound :class:`MessengerService` and inbound ``UpdateDispatcher`` resolve a
provider *by id*. Adding a provider is purely additive — ``bot-base`` never
imports an adapter and adapters never import each other (D10).
"""
from __future__ import annotations

from typing import Dict, List

from plugins.bot_base.bot_base.ports import (
    IMessengerProvider,
    UnknownProviderError,
)


class MessengerProviderRegistry:
    """In-memory registry of provider id → :class:`IMessengerProvider`."""

    def __init__(self) -> None:
        self._providers: Dict[str, IMessengerProvider] = {}

    def register(self, provider: IMessengerProvider) -> None:
        """Register an adapter under its ``provider_id``.

        Re-registering the same id replaces the binding (an adapter
        re-enabling after a config change is expected).
        """
        self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        """Remove a provider; no-op if absent (so ``on_disable`` is safe)."""
        self._providers.pop(provider_id, None)

    def get(self, provider_id: str) -> IMessengerProvider:
        """Resolve a provider by id, or raise a clear :class:`UnknownProviderError`."""
        provider = self._providers.get(provider_id)
        if provider is None:
            raise UnknownProviderError(
                f"No messenger provider registered for id '{provider_id}'. "
                f"Registered: {sorted(self._providers)}"
            )
        return provider

    def has(self, provider_id: str) -> bool:
        return provider_id in self._providers

    def provider_ids(self) -> List[str]:
        return sorted(self._providers)
