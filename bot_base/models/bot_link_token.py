"""BotLinkToken — a one-time deep-link token binding an account to a user (D3)."""
from vbwd.extensions import db
from vbwd.models.base import BaseModel


class BotLinkToken(BaseModel):
    """A short-lived, single-use token issued to a vbwd user.

    The user pastes it into the provider as ``/start <token>``; the adapter
    delivers a :class:`~plugins.bot_base.bot_base.types.BotInbound`, and
    redeeming it binds the inbound external account to ``vbwd_user_id``.
    Single-use: ``redeemed_at`` is stamped on first redemption; a second
    redemption is rejected. Expired (``expires_at`` in the past) is rejected.
    """

    __tablename__ = "bot_base_link_token"

    token = db.Column(db.String(128), nullable=False, unique=True, index=True)
    vbwd_user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("vbwd_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at = db.Column(db.DateTime, nullable=False)
    redeemed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "token": self.token,
            "vbwd_user_id": str(self.vbwd_user_id),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "redeemed_at": self.redeemed_at.isoformat() if self.redeemed_at else None,
        }
