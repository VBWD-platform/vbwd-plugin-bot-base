"""CommandRegistry — collects consumer command providers (D1 inversion).

``bot-base`` asks each *enabled* plugin (via the ``PluginManager``) whether it
structurally implements :class:`BotCommandProvider`; non-implementers are
skipped. ``bot-base`` imports nothing plugin-specific — the dependency points
*inward* (consumers depend on the abstract seam, not the reverse).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from plugins.bot_base.bot_base.ports import BotCommandProvider
from plugins.bot_base.bot_base.types import BotCommand


class CommandRegistry:
    """Resolves :class:`BotCommandProvider`s from the enabled-plugin set."""

    def __init__(self, plugin_manager) -> None:
        self._plugin_manager = plugin_manager

    def get_command_providers(self) -> List[BotCommandProvider]:
        """Every enabled plugin that implements the consumer seam."""
        providers: List[BotCommandProvider] = []
        for plugin in self._plugin_manager.get_enabled_plugins():
            if isinstance(plugin, BotCommandProvider):
                providers.append(plugin)
        return providers

    def get_provider_for_namespace(
        self, namespace: str
    ) -> Optional[BotCommandProvider]:
        """The enabled command provider owning ``namespace``, if any."""
        for provider in self.get_command_providers():
            if provider.bot_namespace == namespace:
                return provider
        return None

    def collect_commands(self) -> List[BotCommand]:
        """The flattened command list across all enabled command providers."""
        commands: List[BotCommand] = []
        for provider in self.get_command_providers():
            commands.extend(provider.get_bot_commands())
        return commands

    def command_index(self) -> Dict[str, BotCommandProvider]:
        """Map of bare command name → owning provider (last writer wins).

        Lets the dispatcher route ``/draw`` to taro without ``bot-base``
        hard-coding any consumer command.
        """
        index: Dict[str, BotCommandProvider] = {}
        for provider in self.get_command_providers():
            for command in provider.get_bot_commands():
                index[command.name] = provider
        return index
