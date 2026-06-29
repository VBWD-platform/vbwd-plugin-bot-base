"""bot-base plugin — provider-neutral bot bridge keystone (S45.0).

Closed for modification, open for adapter extension (Open/Closed): the
``MessengerProviderRegistry`` is the seam adapter plugins (`bot-telegram`,
`bot-meinchat`, ...) register an ``IMessengerProvider`` into on enable, and the
``CommandRegistry`` collects consumer command providers from enabled plugins
(D1). ``bot-base`` imports nothing provider- or consumer-specific.

The plugin class lives **here** (not re-exported). ``on_enable`` registers the
repositories and the singleton services into ``current_app.container``
([[project_plugin_di_provider_registration]]).
"""
from typing import Any, Dict, Optional, TYPE_CHECKING

from flask import current_app

from vbwd.plugins.base import BasePlugin, PluginMetadata

if TYPE_CHECKING:
    from flask import Blueprint


DEFAULT_CONFIG: Dict[str, Any] = {
    "debug_mode": False,
    # How long an issued one-time link token stays redeemable (D3).
    "link_token_ttl_seconds": 900,
    # How long a chat's active conversation owner persists without activity
    # before it is treated as cleared (free text falls back to the menu).
    "conversation_idle_timeout_seconds": 1800,
}


class BotBasePlugin(BasePlugin):
    """Provider-neutral bot core: DTOs, ports, registries, dispatcher, links."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="bot-base",
            version="26.6",
            author="VBWD Team",
            description=(
                "Provider-neutral bot bridge: messenger-provider registry, "
                "outbound MessengerService, inbound command dispatcher, "
                "conversation mode and one-time identity linking."
            ),
            dependencies=[],
        )

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        merged = {**DEFAULT_CONFIG}
        if config:
            merged.update(config)
        super().initialize(merged)

    def get_blueprint(self) -> Optional["Blueprint"]:
        from plugins.bot_base.bot_base.routes import bot_base_bp

        return bot_base_bp

    def get_url_prefix(self) -> Optional[str]:
        return "/api/v1/plugins/bot"

    @property
    def admin_permissions(self):
        return [
            {
                "key": "bot_base.manage",
                "label": "Manage bot linked accounts",
                "group": "Bot",
            },
        ]

    def on_enable(self) -> None:
        from dependency_injector import providers

        from vbwd.plugins.di_helpers import register_repositories
        from plugins.bot_base.bot_base.repositories.bot_link_repository import (
            BotLinkRepository,
        )
        from plugins.bot_base.bot_base.repositories.bot_link_token_repository import (
            BotLinkTokenRepository,
        )
        from plugins.bot_base.bot_base.repositories.bot_session_repository import (
            BotSessionRepository,
        )
        from plugins.bot_base.bot_base.services.messenger_service import (
            MessengerService,
        )
        from plugins.bot_base.bot_base.services.provider_registry import (
            MessengerProviderRegistry,
        )

        container = getattr(current_app, "container", None)
        if container is None:
            return

        register_repositories(
            container,
            {
                "bot_base_link_repository": BotLinkRepository,
                "bot_base_session_repository": BotSessionRepository,
                "bot_base_link_token_repository": BotLinkTokenRepository,
            },
        )

        # The provider registry is a process-wide singleton: adapters register
        # into the *same* instance the MessengerService / dispatcher resolve.
        provider_registry = MessengerProviderRegistry()
        container.messenger_provider_registry = providers.Object(provider_registry)
        container.messenger_service = providers.Factory(
            MessengerService,
            provider_registry=container.messenger_provider_registry,
        )

    def on_disable(self) -> None:
        from vbwd.plugins.di_helpers import unregister_repositories

        container = getattr(current_app, "container", None)
        if container is None:
            return
        unregister_repositories(
            container,
            [
                "bot_base_link_repository",
                "bot_base_session_repository",
                "bot_base_link_token_repository",
            ],
        )
        for attribute in ("messenger_service", "messenger_provider_registry"):
            if hasattr(container, attribute):
                delattr(container, attribute)
