"""Provider-neutral DTOs for the bot bridge (S45.0 / D6 / D7).

These dataclasses are the *only* vocabulary consumers and adapters share.
They carry **no** provider specifics — no ``Telegram*`` / ``Meinchat*`` fields,
no transport details. An adapter normalizes a native update into a
:class:`BotInbound` and renders a :class:`BotReply` natively; a consumer
returns a :class:`BotReply` and never sees the wire format.

Naming follows the full-readable-name rule: ``provider_id``, ``chat_ref``,
``sender_ref``, ``action_data`` — never abbreviations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID


@dataclass(frozen=True)
class ChatRef:
    """A provider-neutral reference to a chat / conversation / channel.

    ``provider_id`` identifies the adapter ("telegram", "meinchat", ...);
    ``chat_id`` is the opaque, provider-scoped chat identifier (a Telegram
    chat id, a meinchat conversation id, a channel handle, ...). The pair is
    globally unique.
    """

    provider_id: str
    chat_id: str


@dataclass(frozen=True)
class BotIdentity:
    """A resolved link between a provider account and a vbwd user.

    Present on a :class:`BotInbound` only when the inbound sender is linked
    (or the provider is auth-native). ``None`` identity means anonymous —
    fine for free commands, rejected for billed/identity actions.
    """

    provider_id: str
    external_user_id: str
    vbwd_user_id: UUID


@dataclass(frozen=True)
class BotCommand:
    """A command a consumer exposes to the bot menu (the ``/help`` listing).

    ``name`` is the bare command without the leading slash ("draw", "balance").
    ``namespace`` is the owning consumer's ``bot_namespace`` ("taro", "chat").
    """

    name: str
    description: str
    namespace: str


@dataclass(frozen=True)
class BotChoice:
    """A tappable choice rendered natively by each provider.

    ``action_data`` is opaque to ``bot-base`` and namespaced
    ``"<plugin>:<action>:<arg>"`` so the dispatcher can route a tapped choice
    back to the owning consumer's ``handle_action`` (D7). ``hint`` is an optional
    short secondary label (e.g. a price string ``"€29/mo"``) a rich provider may
    render right-aligned on the card; it defaults to ``None`` so non-rich
    providers/consumers are unaffected.

    ``url`` is an optional PUBLIC fe route (e.g. ``"/shop/product/blue-shirt"``).
    When present a rich provider's widget NAVIGATES to it on tap instead of
    sending the ``action_data`` back to the bot — so a choice can deep-link to a
    detail page. It defaults to ``None`` (the normal action-dispatch path), so
    every existing choice behaves exactly as before (Liskov).
    """

    label: str
    action_data: str
    hint: Optional[str] = None
    url: Optional[str] = None


@dataclass(frozen=True)
class BotInbound:
    """A normalized inbound update.

    Built by an adapter's ``parse_update``. ``command`` / ``args`` are set for
    a slash command; ``action_data`` is set for a tapped choice; ``text`` is
    the raw free text. ``identity`` is resolved by the dispatcher (or supplied
    directly by an auth-native adapter).
    """

    provider_id: str
    chat_ref: ChatRef
    sender_ref: str
    text: Optional[str] = None
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    action_data: Optional[str] = None
    identity: Optional[BotIdentity] = None


@dataclass(frozen=True)
class BotReply:
    """A normalized outbound reply.

    ``text`` is the message body; ``choices`` are optional tappable choices
    rendered natively by each provider (Telegram inline keyboard, plain
    numbered list, ...).

    ``meta`` is an optional **provider-neutral** structured payload
    ``{"kind": "...", ...}`` (e.g. ``bot_menu`` / ``bot_cart``, or a clean
    ``{"text": ...}`` prompt accompanying ``choices``). It carries NO provider
    specifics and does NOT contain the choices themselves — those stay in
    ``choices``. Each provider's sender translates it natively (meinchat →
    ``message.meta``; a non-rich client ignores it and renders ``text``). It
    defaults to ``None`` so every existing reply behaves exactly as before
    (Liskov).
    """

    text: str
    choices: List[BotChoice] = field(default_factory=list)
    meta: Optional[dict] = None
