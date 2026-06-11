"""UpdateDispatcher — Seam B (inbound), provider-neutral.

Given a normalized :class:`BotInbound`, it:
  1. resolves identity from :class:`BotLinkRepository` (unless the adapter
     already supplied one — auth-native providers),
  2. handles the built-in ``/hello`` · ``/start`` · ``/stop`` · ``/help`` set,
  3. routes a namespaced ``action_data`` tap or a consumer command to that
     consumer's ``handle_action`` (D7),
  4. routes free text to the chat's active conversation owner, or
  5. falls back to the help menu.

It returns the :class:`BotReply` (the caller / route sends it). ``bot-base``
imports nothing plugin-specific; consumers are reached only via the
:class:`CommandRegistry`.
"""
from __future__ import annotations

from typing import List

from plugins.bot_base.bot_base.repositories.bot_link_repository import (
    BotLinkRepository,
)
from plugins.bot_base.bot_base.services.command_registry import CommandRegistry
from plugins.bot_base.bot_base.services.conversation_service import (
    ConversationService,
)
from plugins.bot_base.bot_base.services.link_service import (
    LinkService,
    LinkTokenAlreadyRedeemedError,
    LinkTokenExpiredError,
    LinkTokenInvalidError,
)
from plugins.bot_base.bot_base.types import BotIdentity, BotInbound, BotReply

BUILTIN_NAMESPACE = "bot-base"


class UpdateDispatcher:
    """Routes a normalized inbound update to a reply (built-in or consumer)."""

    def __init__(
        self,
        *,
        command_registry: CommandRegistry,
        conversation_service: ConversationService,
        link_service: LinkService,
        link_repository: BotLinkRepository,
    ) -> None:
        self._command_registry = command_registry
        self._conversation_service = conversation_service
        self._link_service = link_service
        self._link_repository = link_repository

    def dispatch(self, inbound: BotInbound) -> BotReply:
        inbound = self._with_resolved_identity(inbound)

        if inbound.action_data is not None:
            return self._dispatch_action(inbound)

        if inbound.command is not None:
            return self._dispatch_command(inbound)

        return self._dispatch_free_text(inbound)

    # ── identity ────────────────────────────────────────────────────────────
    def _with_resolved_identity(self, inbound: BotInbound) -> BotInbound:
        if inbound.identity is not None:
            return inbound
        link = self._link_repository.find_by_external(
            inbound.provider_id, inbound.sender_ref
        )
        if link is None:
            return inbound
        identity = BotIdentity(
            provider_id=link.provider_id,
            external_user_id=link.external_user_id,
            vbwd_user_id=link.vbwd_user_id,
        )
        return _replace_identity(inbound, identity)

    # ── tapped choice (action_data) ─────────────────────────────────────────
    def _dispatch_action(self, inbound: BotInbound) -> BotReply:
        action_data = inbound.action_data or ""
        namespace = action_data.split(":", 1)[0]
        if namespace == BUILTIN_NAMESPACE:
            return self._help_menu()
        provider = self._command_registry.get_provider_for_namespace(namespace)
        if provider is None:
            return self._help_menu()
        return provider.handle_action(inbound)

    # ── slash command ───────────────────────────────────────────────────────
    def _dispatch_command(self, inbound: BotInbound) -> BotReply:
        command = inbound.command or ""
        if command == "hello":
            return self._hello()
        if command == "start":
            return self._start(inbound)
        if command == "stop":
            return self._stop(inbound)
        if command == "help":
            return self._help_menu()

        provider = self._command_registry.command_index().get(command)
        if provider is None:
            return self._help_menu()
        self._conversation_service.claim(
            inbound.provider_id, inbound.chat_ref.chat_id, provider.bot_namespace
        )
        return provider.handle_action(inbound)

    # ── free text ───────────────────────────────────────────────────────────
    def _dispatch_free_text(self, inbound: BotInbound) -> BotReply:
        owner = self._conversation_service.get_active_owner(
            inbound.provider_id, inbound.chat_ref.chat_id
        )
        if owner is None:
            return self._help_menu()
        provider = self._command_registry.get_provider_for_namespace(owner)
        if provider is None:
            return self._help_menu()
        return provider.handle_action(inbound)

    # ── built-in commands ───────────────────────────────────────────────────
    def _hello(self) -> BotReply:
        return BotReply(text="Hello! I'm the bot. Type /help to see what I can do.")

    def _start(self, inbound: BotInbound) -> BotReply:
        if not inbound.args:
            return BotReply(
                text=(
                    "Send /start <token> with the link token from your account "
                    "to connect this chat."
                )
            )
        token_value = inbound.args[0]
        try:
            self._link_service.redeem_token(
                token_value,
                provider_id=inbound.provider_id,
                external_user_id=inbound.sender_ref,
            )
        except LinkTokenInvalidError:
            return BotReply(text="That link token is not valid.")
        except LinkTokenExpiredError:
            return BotReply(text="That link token has expired. Please request a new one.")
        except LinkTokenAlreadyRedeemedError:
            return BotReply(text="That link token has already been used.")
        return BotReply(text="Your account is now connected.")

    def _stop(self, inbound: BotInbound) -> BotReply:
        self._conversation_service.clear(
            inbound.provider_id, inbound.chat_ref.chat_id
        )
        return BotReply(text="Conversation cleared. Type /help to start again.")

    def _help_menu(self) -> BotReply:
        lines: List[str] = [
            "Available commands:",
            "/hello — say hello",
            "/start <token> — connect your account",
            "/stop — end the current conversation",
            "/help — show this menu",
        ]
        for command in self._command_registry.collect_commands():
            lines.append(f"/{command.name} — {command.description}")
        return BotReply(text="\n".join(lines))


def _replace_identity(inbound: BotInbound, identity: BotIdentity) -> BotInbound:
    """Return a copy of ``inbound`` with ``identity`` set (DTOs are frozen)."""
    return BotInbound(
        provider_id=inbound.provider_id,
        chat_ref=inbound.chat_ref,
        sender_ref=inbound.sender_ref,
        text=inbound.text,
        command=inbound.command,
        args=inbound.args,
        action_data=inbound.action_data,
        identity=identity,
    )
