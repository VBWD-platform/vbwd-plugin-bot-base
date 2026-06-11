"""ConversationService — per-chat active owner with idle timeout.

Conversation mode: a command can *claim* a chat for its namespace so subsequent
free text routes to that consumer's ``handle_action``. The claim is cleared by
``/stop`` or after ``conversation_idle_timeout_seconds`` of inactivity.
"""
from __future__ import annotations

from typing import Optional

from plugins.bot_base.bot_base.models.bot_session import BotSession
from plugins.bot_base.bot_base.repositories.bot_session_repository import (
    BotSessionRepository,
)
from vbwd.utils.datetime_utils import utcnow

DEFAULT_CONVERSATION_IDLE_TIMEOUT_SECONDS = 1800


class ConversationService:
    """Get/set/clear the active conversation owner keyed ``(provider_id, chat_ref)``."""

    def __init__(
        self,
        session_repository: BotSessionRepository,
        *,
        conversation_idle_timeout_seconds: int = (
            DEFAULT_CONVERSATION_IDLE_TIMEOUT_SECONDS
        ),
    ) -> None:
        self._session_repository = session_repository
        self._conversation_idle_timeout_seconds = conversation_idle_timeout_seconds

    def get_active_owner(self, provider_id: str, chat_ref: str) -> Optional[str]:
        """Return the active owner namespace, honoring the idle timeout.

        A session whose ``updated_at`` is older than the idle window is treated
        as having no owner (the stale claim is cleared lazily on read).
        """
        session = self._session_repository.find_by_chat(provider_id, chat_ref)
        if session is None or session.active_plugin is None:
            return None
        if self._is_expired(session):
            session.active_plugin = None
            self._session_repository.save(session)
            return None
        return session.active_plugin

    def claim(self, provider_id: str, chat_ref: str, namespace: str) -> None:
        """Set ``namespace`` as the active owner of the chat."""
        session = self._session_repository.find_by_chat(provider_id, chat_ref)
        if session is None:
            session = BotSession(
                provider_id=provider_id,
                chat_ref=chat_ref,
                active_plugin=namespace,
            )
        else:
            session.active_plugin = namespace
        self._session_repository.save(session)

    def clear(self, provider_id: str, chat_ref: str) -> None:
        """Clear any active owner of the chat (idempotent)."""
        session = self._session_repository.find_by_chat(provider_id, chat_ref)
        if session is None:
            return
        session.active_plugin = None
        self._session_repository.save(session)

    def _is_expired(self, session: BotSession) -> bool:
        last_activity = session.updated_at
        if last_activity is None:
            return False
        idle_seconds = (utcnow() - last_activity).total_seconds()
        return bool(idle_seconds > self._conversation_idle_timeout_seconds)
