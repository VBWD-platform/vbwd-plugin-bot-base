"""ConversationService — claim/clear by namespace; idle timeout clears owner."""
from datetime import timedelta

from plugins.bot_base.bot_base.models.bot_session import BotSession
from plugins.bot_base.bot_base.services.conversation_service import (
    ConversationService,
)
from vbwd.utils.datetime_utils import utcnow


class _FakeSessionRepo:
    def __init__(self):
        self.rows = []

    def find_by_chat(self, provider_id, chat_ref):
        for row in self.rows:
            if row.provider_id == provider_id and row.chat_ref == chat_ref:
                return row
        return None

    def save(self, row):
        if row not in self.rows:
            self.rows.append(row)
        return row

    def delete(self, row):
        self.rows.remove(row)


def test_claim_then_get_active_owner():
    service = ConversationService(_FakeSessionRepo())
    service.claim("telegram", "chat-1", "tarot")

    assert service.get_active_owner("telegram", "chat-1") == "tarot"


def test_no_session_means_no_owner():
    service = ConversationService(_FakeSessionRepo())
    assert service.get_active_owner("telegram", "chat-1") is None


def test_clear_removes_owner():
    service = ConversationService(_FakeSessionRepo())
    service.claim("telegram", "chat-1", "tarot")

    service.clear("telegram", "chat-1")

    assert service.get_active_owner("telegram", "chat-1") is None


def test_idle_timeout_clears_owner():
    repo = _FakeSessionRepo()
    stale = BotSession(provider_id="telegram", chat_ref="chat-1", active_plugin="tarot")
    stale.updated_at = utcnow() - timedelta(seconds=10_000)
    repo.save(stale)
    service = ConversationService(repo, conversation_idle_timeout_seconds=60)

    assert service.get_active_owner("telegram", "chat-1") is None
