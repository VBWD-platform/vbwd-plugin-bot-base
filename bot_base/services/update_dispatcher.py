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

# The built-in command set, as ``{command, description}`` rows. The same rows
# feed both the run-on text fallback (non-rich clients) and the ``bot_menu``
# ``meta`` (rich clients) — one source of truth (DRY).
_BUILTIN_HELP_COMMANDS = (
    {"command": "/hello", "description": "say hello"},
    {"command": "/start", "description": "connect your account"},
    {"command": "/stop", "description": "end the current conversation"},
    {"command": "/help", "description": "show this menu"},
)


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
            # No command has claimed this chat. Before falling back to the help
            # menu, offer the turn to an AMBIENT ANSWERER — an enabled provider
            # that opted in via ``bot_ambient_answerer = True`` (e.g. the LLM
            # sales consultant). This lets a guest just talk, no command needed.
            # Additive + opt-in: no ambient provider → help menu, exactly as before.
            ambient = self._ambient_provider()
            if ambient is not None:
                return ambient.handle_action(inbound)
            return self._help_menu()
        provider = self._command_registry.get_provider_for_namespace(owner)
        if provider is None:
            return self._help_menu()
        return provider.handle_action(inbound)

    def _ambient_provider(self):
        """The first enabled provider that opts into answering unclaimed free
        text (``bot_ambient_answerer = True``), or ``None``."""
        for provider in self._command_registry.get_command_providers():
            if getattr(provider, "bot_ambient_answerer", False):
                return provider
        return None

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
            return BotReply(
                text="That link token has expired. Please request a new one."
            )
        except LinkTokenAlreadyRedeemedError:
            return BotReply(text="That link token has already been used.")
        return BotReply(text="Your account is now connected.")

    def _stop(self, inbound: BotInbound) -> BotReply:
        self._conversation_service.clear(inbound.provider_id, inbound.chat_ref.chat_id)
        return BotReply(text="Conversation cleared. Type /help to start again.")

    def _help_menu(self) -> BotReply:
        command_rows = self._help_command_rows()
        lines: List[str] = ["Available commands:"]
        lines.extend(f"{row['command']} — {row['description']}" for row in command_rows)
        return BotReply(
            text="\n".join(lines),
            meta={"kind": "bot_menu", "commands": command_rows},
        )

    def _help_command_rows(self) -> List[dict]:
        """The built-in commands plus every registered consumer command, as
        ``{command, description}`` rows. No hard-coded plugin knowledge — the
        consumer commands are derived from the :class:`CommandRegistry`, so the
        ``bot_menu`` stays accurate as plugins enable/disable."""
        rows: List[dict] = [dict(row) for row in _BUILTIN_HELP_COMMANDS]
        for command in self._command_registry.collect_commands():
            rows.append(
                {"command": f"/{command.name}", "description": command.description}
            )
        return rows


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
