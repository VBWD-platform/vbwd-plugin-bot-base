"""Flask Blueprint for bot_base — user link management + admin listing.

Single url prefix ``/api/v1/plugins/bot`` (set via the plugin's
``get_url_prefix``), so routes use relative paths.

  * user (``require_auth``): issue a link token + deep-link, read status, unlink.
  * admin (``require_admin`` + ``bot_base.manage``): generic linked-accounts list.

There is deliberately **no** webhook here — inbound transport is each adapter's
concern (S45.1+). Services are built per request from ``db.session`` (the
config knobs come from the plugin's ``config_store`` entry).
"""
from typing import Optional

from flask import Blueprint, current_app, g, jsonify, request

from vbwd.extensions import db
from vbwd.middleware.auth import require_admin, require_auth, require_permission

from plugins.bot_base.bot_base.repositories.bot_link_repository import (
    BotLinkRepository,
)
from plugins.bot_base.bot_base.repositories.bot_link_token_repository import (
    BotLinkTokenRepository,
)
from plugins.bot_base.bot_base.services.link_service import (
    DEFAULT_LINK_TOKEN_TTL_SECONDS,
    LinkService,
)

bot_base_bp = Blueprint("bot_base", __name__)


def _config_value(key: str, default):
    config_store = getattr(current_app, "config_store", None)
    if config_store is None:
        return default
    config = config_store.get_config("bot-base") or {}
    return config.get(key, default)


def _link_service() -> LinkService:
    ttl_seconds = int(
        _config_value("link_token_ttl_seconds", DEFAULT_LINK_TOKEN_TTL_SECONDS)
    )
    return LinkService(
        BotLinkRepository(db.session),
        BotLinkTokenRepository(db.session),
        link_token_ttl_seconds=ttl_seconds,
    )


def _resolve_deeplink(provider_id: str, token_value: str) -> Optional[str]:
    """Ask the named provider for a connect URL, if a provider is registered."""
    container = getattr(current_app, "container", None)
    if container is None:
        return None
    registry = container.messenger_provider_registry()
    if not registry.has(provider_id):
        return None
    return registry.get(provider_id).build_link_deeplink(token_value)


@bot_base_bp.route("/link/start", methods=["POST"])
@require_auth
def start_link():
    """Issue a one-time link token (+ provider deep-link if available)."""
    provider_id = request.args.get("provider", "")
    if not provider_id:
        return jsonify({"error": "Query parameter 'provider' is required"}), 400

    token = _link_service().issue_token(g.user_id)
    db.session.commit()

    deeplink = _resolve_deeplink(provider_id, token.token)
    return (
        jsonify(
            {
                "token": token.token,
                "deeplink": deeplink,
                "expires_at": token.expires_at.isoformat(),
            }
        ),
        201,
    )


@bot_base_bp.route("/link", methods=["GET"])
@require_auth
def link_status():
    """Report whether the current user is linked for the given provider."""
    provider_id = request.args.get("provider", "")
    if not provider_id:
        return jsonify({"error": "Query parameter 'provider' is required"}), 400

    link = _link_service().get_link_for_user(provider_id, g.user_id)
    return jsonify({"linked": link is not None, "link": link.to_dict() if link else None})


@bot_base_bp.route("/link", methods=["DELETE"])
@require_auth
def unlink():
    """Remove the current user's link for the given provider."""
    provider_id = request.args.get("provider", "")
    if not provider_id:
        return jsonify({"error": "Query parameter 'provider' is required"}), 400

    removed = _link_service().unlink(provider_id, g.user_id)
    db.session.commit()
    return jsonify({"unlinked": removed})


@bot_base_bp.route("/admin/links", methods=["GET"])
@require_auth
@require_admin
@require_permission("bot_base.manage")
def admin_list_links():
    """Generic linked-accounts listing across all providers (admin only)."""
    links = BotLinkRepository(db.session).list_all()
    return jsonify({"links": [link.to_dict() for link in links]})
