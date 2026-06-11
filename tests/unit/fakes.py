"""Test doubles that honor the bot_base ports (Liskov: substitutable, no transport).

A ``FakeMessengerProvider`` records every send instead of touching a wire; a
``StubCommandProvider`` is a minimal :class:`BotCommandProvider`. Both let the
inbound/outbound seams be exercised provider-neutrally.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from plugins.bot_base.bot_base.types import (
    BotCommand,
    BotInbound,
    BotReply,
    ChatRef,
)


class FakeMessengerProvider:
    """An ``IMessengerProvider`` that captures sends; never transports."""

    def __init__(self, provider_id: str = "fake") -> None:
        self.provider_id = provider_id
        self.sent: List[Tuple[BotReply, ChatRef]] = []

    def parse_update(self, raw: dict) -> BotInbound:
        chat_ref = ChatRef(provider_id=self.provider_id, chat_id=raw["chat_id"])
        return BotInbound(
            provider_id=self.provider_id,
            chat_ref=chat_ref,
            sender_ref=raw["sender_ref"],
            text=raw.get("text"),
            command=raw.get("command"),
            args=raw.get("args", []),
            action_data=raw.get("action_data"),
        )

    def send(self, reply: BotReply, *, to: ChatRef) -> None:
        self.sent.append((reply, to))

    def build_link_deeplink(self, token: str) -> Optional[str]:
        return f"fake://link/{token}"


class StubCommandProvider:
    """A minimal consumer (``BotCommandProvider``) for dispatcher routing tests."""

    def __init__(self, namespace: str = "demo") -> None:
        self.bot_namespace = namespace
        self.handled: List[BotInbound] = []

    def get_bot_commands(self) -> List[BotCommand]:
        return [
            BotCommand(
                name="demo",
                description="run the demo",
                namespace=self.bot_namespace,
            )
        ]

    def handle_action(self, context: BotInbound) -> BotReply:
        self.handled.append(context)
        return BotReply(text=f"{self.bot_namespace} handled: {context.text or ''}")


class FakePluginManager:
    """Stands in for ``PluginManager.get_enabled_plugins`` in unit specs."""

    def __init__(self, enabled_plugins: List[object]) -> None:
        self._enabled_plugins = enabled_plugins

    def get_enabled_plugins(self) -> List[object]:
        return list(self._enabled_plugins)
