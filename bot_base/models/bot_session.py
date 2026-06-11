"""BotSession — the per-chat active conversation owner (conversation mode)."""
from vbwd.extensions import db
from vbwd.models.base import BaseModel


class BotSession(BaseModel):
    """Tracks which plugin currently owns free-text in a chat.

    Keyed by ``(provider_id, chat_ref)``. ``active_plugin`` is the namespace
    of the consumer that claimed the conversation; ``NULL`` means no owner
    (free text falls through to the help menu). ``updated_at`` (from
    ``BaseModel``) drives idle-timeout expiry.
    """

    __tablename__ = "bot_base_session"

    provider_id = db.Column(db.String(64), nullable=False)
    chat_ref = db.Column(db.String(255), nullable=False)
    active_plugin = db.Column(db.String(128), nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            "provider_id",
            "chat_ref",
            name="uq_bot_base_session_provider_chat",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "provider_id": self.provider_id,
            "chat_ref": self.chat_ref,
            "active_plugin": self.active_plugin,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
