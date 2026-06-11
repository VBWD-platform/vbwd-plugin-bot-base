"""MessengerService — Seam A (outbound), provider-routed.

The single exported entry point any consumer plugin calls to post to a chat or
a channel. It resolves the registered :class:`IMessengerProvider` by id and
delegates to its ``send``; an unregistered/disabled provider raises a clear
:class:`UnknownProviderError` (never a silent drop).
"""
from __future__ import annotations

from typing import List, Optional

from plugins.bot_base.bot_base.services.provider_registry import (
    MessengerProviderRegistry,
)
from plugins.bot_base.bot_base.types import BotChoice, BotReply, ChatRef


class MessengerService:
    """Outbound bridge: ``send_to_chat`` / ``send_to_channel`` by provider id."""

    def __init__(self, provider_registry: MessengerProviderRegistry) -> None:
        self._provider_registry = provider_registry

    def send_to_chat(
        self,
        provider_id: str,
        chat_id: str,
        text: str,
        *,
        choices: Optional[List[BotChoice]] = None,
    ) -> None:
        """Send a reply to a specific chat on the named provider."""
        provider = self._provider_registry.get(provider_id)
        reply = BotReply(text=text, choices=list(choices) if choices else [])
        provider.send(reply, to=ChatRef(provider_id=provider_id, chat_id=chat_id))

    def send_to_channel(
        self,
        provider_id: str,
        channel: str,
        text: str,
        *,
        choices: Optional[List[BotChoice]] = None,
    ) -> None:
        """Send a reply to a channel/broadcast target on the named provider.

        A channel is just a chat whose id is the channel handle, so this routes
        through the same provider ``send`` — keeping one home for delivery (DRY).
        """
        self.send_to_chat(provider_id, channel, text, choices=choices)
