"""LinkService (D3) — issue → redeem binds; expired + double-redeem rejected.

Uses a tiny in-memory fake for the two repositories so token state (the
``redeemed_at`` flip) persists across calls within a test — a ``MagicMock``
would not retain the saved row.
"""
from datetime import timedelta
from uuid import uuid4

import pytest

from plugins.bot_base.bot_base.models.bot_link import BotLink
from plugins.bot_base.bot_base.models.bot_link_token import BotLinkToken
from plugins.bot_base.bot_base.services.link_service import (
    LinkService,
    LinkTokenAlreadyRedeemedError,
    LinkTokenExpiredError,
    LinkTokenInvalidError,
)
from vbwd.utils.datetime_utils import utcnow


class _FakeTokenRepo:
    def __init__(self):
        self.rows = {}

    def find_by_token(self, token):
        return self.rows.get(token)

    def save(self, row):
        self.rows[row.token] = row
        return row


class _FakeLinkRepo:
    def __init__(self):
        self.rows = []

    def find_by_external(self, provider_id, external_user_id):
        for row in self.rows:
            if (
                row.provider_id == provider_id
                and row.external_user_id == external_user_id
            ):
                return row
        return None

    def find_by_user(self, provider_id, vbwd_user_id):
        for row in self.rows:
            if row.provider_id == provider_id and row.vbwd_user_id == vbwd_user_id:
                return row
        return None

    def save(self, row):
        if row not in self.rows:
            self.rows.append(row)
        return row

    def delete(self, row):
        self.rows.remove(row)


def _service():
    return LinkService(_FakeLinkRepo(), _FakeTokenRepo(), link_token_ttl_seconds=900)


def test_issue_then_redeem_binds_external_account_to_user():
    service = _service()
    user_id = uuid4()
    token = service.issue_token(user_id)

    link = service.redeem_token(
        token.token, provider_id="telegram", external_user_id="tg-42"
    )

    assert isinstance(link, BotLink)
    assert link.vbwd_user_id == user_id
    assert link.external_user_id == "tg-42"
    assert link.provider_id == "telegram"
    assert link.linked_at is not None


def test_redeem_unknown_token_rejected():
    service = _service()
    with pytest.raises(LinkTokenInvalidError):
        service.redeem_token(
            "nope", provider_id="telegram", external_user_id="tg-1"
        )


def test_expired_token_rejected():
    link_repo = _FakeLinkRepo()
    token_repo = _FakeTokenRepo()
    expired = BotLinkToken(
        token="expired-token",
        vbwd_user_id=uuid4(),
        expires_at=utcnow() - timedelta(seconds=1),
        redeemed_at=None,
    )
    token_repo.save(expired)
    service = LinkService(link_repo, token_repo)

    with pytest.raises(LinkTokenExpiredError):
        service.redeem_token(
            "expired-token", provider_id="telegram", external_user_id="tg-1"
        )


def test_double_redeem_rejected():
    service = _service()
    token = service.issue_token(uuid4())
    service.redeem_token(
        token.token, provider_id="telegram", external_user_id="tg-1"
    )

    with pytest.raises(LinkTokenAlreadyRedeemedError):
        service.redeem_token(
            token.token, provider_id="telegram", external_user_id="tg-1"
        )
