"""BotLink — the verified link between a provider account and a vbwd user (D3)."""
from vbwd.extensions import db
from vbwd.models.base import BaseModel


class BotLink(BaseModel):
    """One row per (provider, external account) ↔ vbwd user binding.

    Created when a ``/start <token>`` deep-link is redeemed (or directly by an
    auth-native adapter). The ``(provider_id, external_user_id)`` pair is the
    natural key; it is unique so an external account links to at most one user.
    """

    __tablename__ = "bot_base_link"

    provider_id = db.Column(db.String(64), nullable=False, index=True)
    external_user_id = db.Column(db.String(255), nullable=False)
    vbwd_user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("vbwd_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bot_ref = db.Column(db.String(255), nullable=True)
    linked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            "provider_id",
            "external_user_id",
            name="uq_bot_base_link_provider_external",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "provider_id": self.provider_id,
            "external_user_id": self.external_user_id,
            "vbwd_user_id": str(self.vbwd_user_id),
            "bot_ref": self.bot_ref,
            "linked_at": self.linked_at.isoformat() if self.linked_at else None,
        }
