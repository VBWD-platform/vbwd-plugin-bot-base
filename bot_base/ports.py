"""Ports (SPIs) for the bot bridge — the contracts adapters and consumers implement.

Two extension axes (D10):

* **Providers** implement :class:`IMessengerProvider` and self-register into the
  :class:`~plugins.bot_base.bot_base.services.provider_registry.MessengerProviderRegistry`.
  A new provider is purely additive — ``bot-base`` never imports an adapter.
* **Consumers** implement :class:`BotCommandProvider`; ``bot-base`` collects them
  from enabled plugins (D1 inversion). A consumer references only these abstract
  types and the neutral DTOs — never any ``Telegram*`` / ``Meinchat*`` class.

Both are :class:`typing.Protocol`s (structural / runtime-checkable) so neither
adapters nor consumers must import a base class from ``bot-base`` — they only
depend on the shape (Open/Closed, narrow interfaces).
"""
from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from plugins.bot_base.bot_base.types import (
    BotCommand,
    BotInbound,
    BotReply,
    ChatRef,
)


class UnknownProviderError(LookupError):
    """Raised when a provider id is not registered in the provider registry.

    A clear, typed error (never a silent ``None``) so a misconfigured call
    site / disabled adapter surfaces loudly instead of dropping the message.
    """


@runtime_checkable
class IMessengerProvider(Protocol):
    """The SPI an adapter plugin implements (D6).

    The transport lifecycle (webhook / long-poll / event subscription) is
    provider-specific and stays in the adapter — it is **not** part of this
    port.
    """

    provider_id: str

    def parse_update(self, raw: dict) -> BotInbound:
        """Normalize a native inbound payload into a :class:`BotInbound`."""
        ...

    def send(self, reply: BotReply, *, to: ChatRef) -> None:
        """Render and deliver a normalized reply to the given chat."""
        ...

    def build_link_deeplink(self, token: str) -> Optional[str]:
        """Provider-specific connect URL for a link token, or ``None``."""
        ...


@runtime_checkable
class BotCommandProvider(Protocol):
    """The consumer seam (D1) — a plugin that exposes bot commands.

    ``bot-base`` discovers implementers among the *enabled* plugins via the
    :class:`~vbwd.plugins.manager.PluginManager`; non-implementers are skipped.
    """

    bot_namespace: str

    def get_bot_commands(self) -> List[BotCommand]:
        """The commands this consumer contributes to the ``/help`` menu."""
        ...

    def handle_action(self, context: BotInbound) -> BotReply:
        """Handle a command / free-text / tapped-choice update for this namespace."""
        ...
