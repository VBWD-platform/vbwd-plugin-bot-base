"""LinkService — issue + redeem one-time identity-link tokens (D3).

A vbwd user requests a token; the user pastes it into the provider as
``/start <token>``; redeeming it binds the inbound external account to the
user's id. Tokens are single-use and short-lived: a second redemption or an
expired token is rejected with a clear typed error.
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Optional
from uuid import UUID

from plugins.bot_base.bot_base.models.bot_link import BotLink
from plugins.bot_base.bot_base.models.bot_link_token import BotLinkToken
from plugins.bot_base.bot_base.repositories.bot_link_repository import (
    BotLinkRepository,
)
from plugins.bot_base.bot_base.repositories.bot_link_token_repository import (
    BotLinkTokenRepository,
)
from vbwd.utils.datetime_utils import utcnow

DEFAULT_LINK_TOKEN_TTL_SECONDS = 900
_TOKEN_BYTES = 24


class LinkTokenInvalidError(Exception):
    """Raised when a link token is unknown."""


class LinkTokenExpiredError(Exception):
    """Raised when a link token's ``expires_at`` is in the past."""


class LinkTokenAlreadyRedeemedError(Exception):
    """Raised when a link token has already been redeemed (single-use)."""


class LinkService:
    """Issue and redeem one-time link tokens; manage the resulting links."""

    def __init__(
        self,
        link_repository: BotLinkRepository,
        link_token_repository: BotLinkTokenRepository,
        *,
        link_token_ttl_seconds: int = DEFAULT_LINK_TOKEN_TTL_SECONDS,
    ) -> None:
        self._link_repository = link_repository
        self._link_token_repository = link_token_repository
        self._link_token_ttl_seconds = link_token_ttl_seconds

    def issue_token(self, vbwd_user_id: UUID) -> BotLinkToken:
        """Mint a fresh single-use token for ``vbwd_user_id``."""
        token = BotLinkToken(
            token=secrets.token_urlsafe(_TOKEN_BYTES),
            vbwd_user_id=vbwd_user_id,
            expires_at=utcnow() + timedelta(seconds=self._link_token_ttl_seconds),
            redeemed_at=None,
        )
        return self._link_token_repository.save(token)

    def redeem_token(
        self,
        token_value: str,
        *,
        provider_id: str,
        external_user_id: str,
        bot_ref: Optional[str] = None,
    ) -> BotLink:
        """Redeem a token and bind the external account to the token's user.

        Raises :class:`LinkTokenInvalidError` / :class:`LinkTokenExpiredError` /
        :class:`LinkTokenAlreadyRedeemedError` on the respective failure.
        """
        token = self._link_token_repository.find_by_token(token_value)
        if token is None:
            raise LinkTokenInvalidError(f"Unknown link token '{token_value}'.")
        if token.redeemed_at is not None:
            raise LinkTokenAlreadyRedeemedError("Link token already redeemed.")
        if token.expires_at <= utcnow():
            raise LinkTokenExpiredError("Link token has expired.")

        token.redeemed_at = utcnow()
        self._link_token_repository.save(token)

        existing = self._link_repository.find_by_external(provider_id, external_user_id)
        if existing is not None:
            existing.vbwd_user_id = token.vbwd_user_id
            existing.bot_ref = bot_ref
            existing.linked_at = utcnow()
            return self._link_repository.save(existing)

        link = BotLink(
            provider_id=provider_id,
            external_user_id=external_user_id,
            vbwd_user_id=token.vbwd_user_id,
            bot_ref=bot_ref,
            linked_at=utcnow(),
        )
        return self._link_repository.save(link)

    def get_link_for_user(
        self, provider_id: str, vbwd_user_id: UUID
    ) -> Optional[BotLink]:
        return self._link_repository.find_by_user(provider_id, vbwd_user_id)

    def unlink(self, provider_id: str, vbwd_user_id: UUID) -> bool:
        """Remove the user's link for the provider; return whether one existed."""
        link = self._link_repository.find_by_user(provider_id, vbwd_user_id)
        if link is None:
            return False
        self._link_repository.delete(link)
        return True
