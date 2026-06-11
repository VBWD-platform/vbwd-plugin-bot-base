"""S70.3 — provider-neutral rich message kinds on the bot DTOs.

``BotChoice`` gains an optional ``hint`` (e.g. a price string) and ``BotReply``
gains an optional provider-neutral ``meta`` (``{"kind": ...}``). Both default to
``None`` so every existing consumer/adapter/test keeps working unchanged
(Liskov — non-rich callers behave exactly as before).

The built-in ``/help`` now emits a ``bot_menu`` ``meta`` listing the built-in
commands AND the collected consumer commands, while keeping the run-on text body
as the universal fallback for non-rich clients.
"""
from plugins.bot_base.bot_base.types import BotChoice, BotReply
from plugins.bot_base.tests.unit.fakes import (
    FakeMessengerProvider,
    StubCommandProvider,
)
from plugins.bot_base.tests.unit.test_update_dispatcher import _build, _inbound


class TestDtoBackCompat:
    def test_bot_choice_hint_defaults_to_none(self):
        choice = BotChoice(label="Pro", action_data="subscription:plan:42")
        assert choice.hint is None

    def test_bot_choice_accepts_hint(self):
        choice = BotChoice(
            label="Pro", action_data="subscription:plan:42", hint="€29/mo"
        )
        assert choice.hint == "€29/mo"

    def test_bot_reply_meta_defaults_to_none(self):
        reply = BotReply(text="Hello")
        assert reply.meta is None

    def test_bot_reply_accepts_meta(self):
        reply = BotReply(text="Hello", meta={"kind": "bot_menu", "commands": []})
        assert reply.meta == {"kind": "bot_menu", "commands": []}


class TestHelpEmitsBotMenu:
    def test_help_meta_is_bot_menu_with_builtins(self):
        dispatcher, *_ = _build()
        provider = FakeMessengerProvider("telegram")

        reply = dispatcher.dispatch(_inbound(provider, command="help"))

        assert reply.meta is not None
        assert reply.meta["kind"] == "bot_menu"
        commands = {
            row["command"]: row["description"] for row in reply.meta["commands"]
        }
        for builtin in ("/hello", "/start", "/stop", "/help"):
            assert builtin in commands

    def test_help_meta_includes_registered_consumer_commands(self):
        dispatcher, *_ = _build(enabled_plugins=[StubCommandProvider("demo")])
        provider = FakeMessengerProvider("telegram")

        reply = dispatcher.dispatch(_inbound(provider, command="help"))

        commands = {
            row["command"]: row["description"] for row in reply.meta["commands"]
        }
        assert commands["/demo"] == "run the demo"

    def test_help_keeps_text_body_as_fallback(self):
        dispatcher, *_ = _build(enabled_plugins=[StubCommandProvider("demo")])
        provider = FakeMessengerProvider("telegram")

        reply = dispatcher.dispatch(_inbound(provider, command="help"))

        assert "Available commands" in reply.text
        assert "/hello" in reply.text
        assert "/demo" in reply.text

    def test_command_row_is_the_command_text(self):
        """A bot_menu row tap is just the command text sent as a body — verify
        the rows carry the leading-slash command so the fe can resend them."""
        dispatcher, *_ = _build(enabled_plugins=[StubCommandProvider("demo")])
        provider = FakeMessengerProvider("telegram")

        reply = dispatcher.dispatch(_inbound(provider, command="help"))

        for row in reply.meta["commands"]:
            assert row["command"].startswith("/")
            assert isinstance(row["description"], str)
