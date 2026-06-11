"""Data access for ``bot_base_link`` rows."""
from typing import List, Optional

from plugins.bot_base.bot_base.models.bot_link import BotLink


class BotLinkRepository:
    """Thin wrapper over the SQLAlchemy session for :class:`BotLink`."""

    def __init__(self, session) -> None:
        self._session = session

    def find_by_external(
        self, provider_id: str, external_user_id: str
    ) -> Optional[BotLink]:
        return (
            self._session.query(BotLink)
            .filter(BotLink.provider_id == provider_id)
            .filter(BotLink.external_user_id == external_user_id)
            .one_or_none()
        )

    def find_by_user(self, provider_id: str, vbwd_user_id) -> Optional[BotLink]:
        return (
            self._session.query(BotLink)
            .filter(BotLink.provider_id == provider_id)
            .filter(BotLink.vbwd_user_id == vbwd_user_id)
            .one_or_none()
        )

    def list_all(self) -> List[BotLink]:
        return self._session.query(BotLink).order_by(BotLink.linked_at).all()

    def save(self, row: BotLink) -> BotLink:
        self._session.add(row)
        self._session.flush()
        return row

    def delete(self, row: BotLink) -> None:
        self._session.delete(row)
        self._session.flush()
