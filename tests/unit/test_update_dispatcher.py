"""UpdateDispatcher (Seam B) — built-ins + routing matrix, provider-neutral.

Exercised entirely through the fake provider's ``parse_update`` + the stub
command provider — no transport, no Telegram/meinchat anything.
"""
from uuid import uuid4

from plugins.bot_base.bot_base.services.command_registry import CommandRegistry
from plugins.bot_base.bot_base.services.conversation_service import (
    ConversationService,
)
from plugins.bot_base.bot_base.services.link_service import LinkService
from plugins.bot_base.bot_base.services.update_dispatcher import UpdateDispatcher
from plugins.bot_base.tests.unit.fakes import (
    FakeMessengerProvider,
    FakePluginManager,
    StubCommandProvider,
)
from plugins.bot_base.tests.unit.test_conversation_service import _FakeSessionRepo
from plugins.bot_base.tests.unit.test_link_service import (
    _FakeLinkRepo,
    _FakeTokenRepo,
)


def _build(enabled_plugins=None, link_repo=None, token_repo=None):
    link_repo = link_repo or _FakeLinkRepo()
    token_repo = token_repo or _FakeTokenRepo()
    command_registry = CommandRegistry(FakePluginManager(enabled_plugins or []))
    conversation_service = ConversationService(_FakeSessionRepo())
    link_service = LinkService(link_repo, token_repo)
    dispatcher = UpdateDispatcher(
        command_registry=command_registry,
        conversation_service=conversation_service,
        link_service=link_service,
        link_repository=link_repo,
    )
    return dispatcher, conversation_service, link_service, link_repo, token_repo


def _inbound(provider, **raw):
    raw.setdefault("chat_id", "chat-1")
    raw.setdefault("sender_ref", "tg-1")
    return provider.parse_update(raw)


def test_hello_returns_greeting():
    dispatcher, *_ = _build()
    provider = FakeMessengerProvider("telegram")

    reply = dispatcher.dispatch(_inbound(provider, command="hello"))

    assert "Hello" in reply.text


def test_unknown_command_returns_help_menu():
    dispatcher, *_ = _build()
    provider = FakeMessengerProvider("telegram")

    reply = dispatcher.dispatch(_inbound(provider, command="does-not-exist"))

    assert "Available commands" in reply.text
    assert "/hello" in reply.text


def test_help_lists_consumer_commands():
    dispatcher, *_ = _build(enabled_plugins=[StubCommandProvider("demo")])
    provider = FakeMessengerProvider("telegram")

    reply = dispatcher.dispatch(_inbound(provider, command="help"))

    assert "/demo" in reply.text
    assert "run the demo" in reply.text


def test_consumer_command_claims_conversation_and_routes():
    stub = StubCommandProvider("demo")
    dispatcher, conversation_service, *_ = _build(enabled_plugins=[stub])
    provider = FakeMessengerProvider("telegram")

    reply = dispatcher.dispatch(_inbound(provider, command="demo", text="/demo"))

    assert "demo handled" in reply.text
    assert conversation_service.get_active_owner("telegram", "chat-1") == "demo"


def test_free_text_with_active_owner_routes_to_that_handler():
    stub = StubCommandProvider("demo")
    dispatcher, conversation_service, *_ = _build(enabled_plugins=[stub])
    conversation_service.claim("telegram", "chat-1", "demo")
    provider = FakeMessengerProvider("telegram")

    reply = dispatcher.dispatch(_inbound(provider, text="hello there"))

    assert "demo handled: hello there" == reply.text
    assert stub.handled[-1].text == "hello there"


def test_free_text_without_owner_returns_menu():
    dispatcher, *_ = _build(enabled_plugins=[StubCommandProvider("demo")])
    provider = FakeMessengerProvider("telegram")

    reply = dispatcher.dispatch(_inbound(provider, text="random text"))

    assert "Available commands" in reply.text


def test_action_data_routed_by_namespace_to_handle_action():
    stub = StubCommandProvider("demo")
    dispatcher, *_ = _build(enabled_plugins=[stub])
    provider = FakeMessengerProvider("telegram")

    reply = dispatcher.dispatch(
        _inbound(provider, action_data="demo:confirm:1")
    )

    assert "demo handled" in reply.text
    assert stub.handled[-1].action_data == "demo:confirm:1"


def test_action_data_unknown_namespace_returns_menu():
    dispatcher, *_ = _build()
    provider = FakeMessengerProvider("telegram")

    reply = dispatcher.dispatch(_inbound(provider, action_data="ghost:x:1"))

    assert "Available commands" in reply.text


def test_stop_clears_conversation_owner():
    stub = StubCommandProvider("demo")
    dispatcher, conversation_service, *_ = _build(enabled_plugins=[stub])
    conversation_service.claim("telegram", "chat-1", "demo")
    provider = FakeMessengerProvider("telegram")

    reply = dispatcher.dispatch(_inbound(provider, command="stop"))

    assert "cleared" in reply.text.lower()
    assert conversation_service.get_active_owner("telegram", "chat-1") is None


def test_start_redeems_token_and_links_account():
    link_repo = _FakeLinkRepo()
    token_repo = _FakeTokenRepo()
    dispatcher, _conv, link_service, _lr, _tr = _build(
        link_repo=link_repo, token_repo=token_repo
    )
    user_id = uuid4()
    token = link_service.issue_token(user_id)
    provider = FakeMessengerProvider("telegram")

    inbound = provider.parse_update(
        {
            "chat_id": "chat-1",
            "sender_ref": "tg-99",
            "command": "start",
            "args": [token.token],
        }
    )
    reply = dispatcher.dispatch(inbound)

    assert "connected" in reply.text.lower()
    link = link_repo.find_by_external("telegram", "tg-99")
    assert link is not None
    assert link.vbwd_user_id == user_id


def test_start_with_bad_token_returns_clear_message():
    dispatcher, *_ = _build()
    provider = FakeMessengerProvider("telegram")

    inbound = provider.parse_update(
        {
            "chat_id": "chat-1",
            "sender_ref": "tg-1",
            "command": "start",
            "args": ["bogus"],
        }
    )
    reply = dispatcher.dispatch(inbound)

    assert "not valid" in reply.text.lower()


def test_dispatcher_resolves_identity_from_link_repository():
    """A linked sender gets identity attached before reaching the handler."""
    from plugins.bot_base.bot_base.models.bot_link import BotLink

    link_repo = _FakeLinkRepo()
    user_id = uuid4()
    link_repo.save(
        BotLink(
            provider_id="telegram",
            external_user_id="tg-1",
            vbwd_user_id=user_id,
        )
    )
    stub = StubCommandProvider("demo")
    dispatcher, conversation_service, *_ = _build(
        enabled_plugins=[stub], link_repo=link_repo
    )
    conversation_service.claim("telegram", "chat-1", "demo")
    provider = FakeMessengerProvider("telegram")

    dispatcher.dispatch(_inbound(provider, text="hi"))

    assert stub.handled[-1].identity is not None
    assert stub.handled[-1].identity.vbwd_user_id == user_id
