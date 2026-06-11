"""Data access for ``bot_base_session`` rows."""
from typing import Optional

from plugins.bot_base.bot_base.models.bot_session import BotSession


class BotSessionRepository:
    """Thin wrapper over the SQLAlchemy session for :class:`BotSession`."""

    def __init__(self, session) -> None:
        self._session = session

    def find_by_chat(self, provider_id: str, chat_ref: str) -> Optional[BotSession]:
        return (
            self._session.query(BotSession)
            .filter(BotSession.provider_id == provider_id)
            .filter(BotSession.chat_ref == chat_ref)
            .one_or_none()
        )

    def save(self, row: BotSession) -> BotSession:
        self._session.add(row)
        self._session.flush()
        return row

    def delete(self, row: BotSession) -> None:
        self._session.delete(row)
        self._session.flush()
