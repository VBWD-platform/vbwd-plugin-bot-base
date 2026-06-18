# bot-base — importable artifacts

**None.** `bot-base` is a transport-neutral library: it owns no CMS widget,
layout, page, or any other data-exchange entity. It ships only DTOs, ports,
registries, the command dispatcher, conversation-mode state and one-time
identity-link tokens — runtime substrate other plugins build on, not portable
content.

There is therefore nothing to import here, and no envelope is fabricated for it.

Importable artifacts owned by the bot stack live in the consuming plugins:

- `bot-meinchat` ships a default conversation-style envelope
  (`bot_conversation_styles`) — see `plugins/bot_meinchat/docs/import/`.
- `bot-meinchat-llm` ships the `/consultant` CMS layout + page envelopes
  (`cms_layouts` / `cms_posts`) — see `plugins/bot_meinchat_llm/docs/import/`.
