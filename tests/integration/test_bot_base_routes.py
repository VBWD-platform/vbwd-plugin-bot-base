"""Integration: bot_base routes — permission enforcement + link round-trip.

Boots the full app (bot-base enabled via plugins.json) so the container has the
provider registry and the blueprint is mounted under ``/api/v1/plugins/bot``.
Test data is created only through the core ``auth_service`` (never raw SQL).
"""
import uuid

import pytest

from vbwd.models.enums import UserRole


def _register_user(app, email: str) -> tuple[str, str]:
    """Register a fresh user through the core auth service; return (id, token)."""
    from vbwd.extensions import db
    from vbwd.repositories.user_repository import UserRepository

    auth_service = app.container.auth_service()
    unique_email = email.replace("@", f"+{uuid.uuid4().hex[:8]}@")
    result = auth_service.register(email=unique_email, password="BotBaseTest123@")
    db.session.commit()
    user = UserRepository(db.session).find_by_id(result.user_id)
    return str(user.id), result.token


def _promote_to_admin(app, user_id: str) -> None:
    from vbwd.extensions import db
    from vbwd.repositories.user_repository import UserRepository

    repository = UserRepository(db.session)
    user = repository.find_by_id(user_id)
    user.role = UserRole.ADMIN
    db.session.commit()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
def test_admin_links_requires_authentication(client):
    response = client.get("/api/v1/plugins/bot/admin/links")
    assert response.status_code == 401


@pytest.mark.integration
def test_admin_links_forbidden_for_regular_user(app, client):
    with app.app_context():
        _user_id, token = _register_user(app, "plain@example.com")

    response = client.get("/api/v1/plugins/bot/admin/links", headers=_auth(token))
    assert response.status_code == 403


@pytest.mark.integration
def test_admin_links_allows_admin_with_permission(app, client):
    with app.app_context():
        user_id, token = _register_user(app, "boss@example.com")
        _promote_to_admin(app, user_id)

    response = client.get("/api/v1/plugins/bot/admin/links", headers=_auth(token))
    assert response.status_code == 200
    assert "links" in response.get_json()


@pytest.mark.integration
def test_link_start_then_redeem_links_account(app, client):
    """/link/start issues a token; redeeming it via LinkService binds the
    external account; the link then surfaces in the admin listing."""
    with app.app_context():
        user_id, token = _register_user(app, "linker@example.com")

    start = client.post(
        "/api/v1/plugins/bot/link/start?provider=telegram", headers=_auth(token)
    )
    assert start.status_code == 201
    payload = start.get_json()
    assert payload["token"]
    # No telegram adapter is registered in this base-only test, so deeplink None.
    assert payload["deeplink"] is None

    # Redeem the token the way an adapter's /start handler would (D3),
    # through the same LinkService the dispatcher uses.
    with app.app_context():
        from vbwd.extensions import db
        from plugins.bot_base.bot_base.repositories.bot_link_repository import (
            BotLinkRepository,
        )
        from plugins.bot_base.bot_base.repositories.bot_link_token_repository import (
            BotLinkTokenRepository,
        )
        from plugins.bot_base.bot_base.services.link_service import LinkService

        link_service = LinkService(
            BotLinkRepository(db.session), BotLinkTokenRepository(db.session)
        )
        link = link_service.redeem_token(
            payload["token"],
            provider_id="telegram",
            external_user_id="tg-round-trip",
        )
        db.session.commit()
        assert str(link.vbwd_user_id) == user_id

    status = client.get(
        "/api/v1/plugins/bot/link?provider=telegram", headers=_auth(token)
    )
    assert status.status_code == 200
    assert status.get_json()["linked"] is True


@pytest.mark.integration
def test_link_start_requires_provider_param(app, client):
    with app.app_context():
        _user_id, token = _register_user(app, "noprov@example.com")

    response = client.post("/api/v1/plugins/bot/link/start", headers=_auth(token))
    assert response.status_code == 400
