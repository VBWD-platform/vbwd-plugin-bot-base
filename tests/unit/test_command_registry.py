"""CommandRegistry (D1) — collects only enabled BotCommandProviders."""
from plugins.bot_base.bot_base.services.command_registry import CommandRegistry
from plugins.bot_base.tests.unit.fakes import (
    FakePluginManager,
    StubCommandProvider,
)


class _NotACommandProvider:
    """An enabled plugin that does NOT implement the consumer seam."""


def test_collects_only_command_providers():
    demo = StubCommandProvider("demo")
    registry = CommandRegistry(
        FakePluginManager([demo, _NotACommandProvider()])
    )

    providers = registry.get_command_providers()

    assert providers == [demo]


def test_collect_commands_flattens_across_providers():
    registry = CommandRegistry(
        FakePluginManager([StubCommandProvider("a"), StubCommandProvider("b")])
    )

    names = {command.name for command in registry.collect_commands()}

    assert names == {"demo"}
    assert len(registry.collect_commands()) == 2


def test_get_provider_for_namespace():
    demo = StubCommandProvider("taro")
    registry = CommandRegistry(FakePluginManager([demo]))

    assert registry.get_provider_for_namespace("taro") is demo
    assert registry.get_provider_for_namespace("missing") is None


def test_command_index_maps_command_name_to_provider():
    demo = StubCommandProvider("demo")
    registry = CommandRegistry(FakePluginManager([demo]))

    index = registry.command_index()

    assert index["demo"] is demo
