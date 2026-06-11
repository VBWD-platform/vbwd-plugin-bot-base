"""SQLAlchemy models for the bot bridge.

Importing this package registers ``bot_base_link``, ``bot_base_session`` and
``bot_base_link_token`` with SQLAlchemy so ``db.create_all()`` / the migration
build them alongside core.
"""
from plugins.bot_base.bot_base.models.bot_link import BotLink
from plugins.bot_base.bot_base.models.bot_link_token import BotLinkToken
from plugins.bot_base.bot_base.models.bot_session import BotSession

__all__ = ["BotLink", "BotLinkToken", "BotSession"]
