"""MessengerService (Seam A) — provider-routed outbound, clear error on miss."""
import pytest

from plugins.bot_base.bot_base.ports import UnknownProviderError
from plugins.bot_base.bot_base.services.messenger_service import MessengerService
from plugins.bot_base.bot_base.services.provider_registry import (
    MessengerProviderRegistry,
)
from plugins.bot_base.bot_base.types import BotChoice
from plugins.bot_base.tests.unit.fakes import FakeMessengerProvider


def _service_with(provider: FakeMessengerProvider) -> MessengerService:
    registry = MessengerProviderRegistry()
    registry.register(provider)
    return MessengerService(registry)


def test_send_to_chat_resolves_provider_by_id_and_sends():
    provider = FakeMessengerProvider("telegram")
    service = _service_with(provider)

    service.send_to_chat("telegram", "chat-1", "hi there")

    assert len(provider.sent) == 1
    reply, chat_ref = provider.sent[0]
    assert reply.text == "hi there"
    assert chat_ref.provider_id == "telegram"
    assert chat_ref.chat_id == "chat-1"


def test_send_to_chat_passes_choices_through():
    provider = FakeMessengerProvider("telegram")
    service = _service_with(provider)
    choices = [BotChoice(label="Yes", action_data="demo:confirm:1")]

    service.send_to_chat("telegram", "chat-1", "pick", choices=choices)

    reply, _ = provider.sent[0]
    assert reply.choices == choices


def test_send_to_channel_routes_through_provider_send():
    provider = FakeMessengerProvider("telegram")
    service = _service_with(provider)

    service.send_to_channel("telegram", "@news", "new post")

    reply, chat_ref = provider.sent[0]
    assert reply.text == "new post"
    assert chat_ref.chat_id == "@news"


def test_unregistered_provider_raises_clear_error():
    service = MessengerService(MessengerProviderRegistry())

    with pytest.raises(UnknownProviderError) as excinfo:
        service.send_to_chat("nope", "chat-1", "hi")

    assert "nope" in str(excinfo.value)
