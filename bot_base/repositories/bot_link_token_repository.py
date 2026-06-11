"""Data access for ``bot_base_link_token`` rows."""
from typing import Optional

from plugins.bot_base.bot_base.models.bot_link_token import BotLinkToken


class BotLinkTokenRepository:
    """Thin wrapper over the SQLAlchemy session for :class:`BotLinkToken`."""

    def __init__(self, session) -> None:
        self._session = session

    def find_by_token(self, token: str) -> Optional[BotLinkToken]:
        return (
            self._session.query(BotLinkToken)
            .filter(BotLinkToken.token == token)
            .one_or_none()
        )

    def save(self, row: BotLinkToken) -> BotLinkToken:
        self._session.add(row)
        self._session.flush()
        return row
