# bot-base

The provider-neutral **bot bridge keystone**. It is a transport-neutral library:
the rich-message + command/link/session substrate every bot adapter and consumer
builds on. It is closed for modification, open for adapter extension
(Open/Closed) — `bot-base` imports nothing provider- or consumer-specific.

## What it does

- **Neutral DTOs** — `BotCommand`, `BotInbound`, `BotReply`, rich-message
  building blocks (text, links, choices) the whole stack shares.
- **Messenger-provider registry** — `MessengerProviderRegistry`, a process-wide
  singleton an adapter plugin (`bot-meinchat`, `bot-telegram`, ...) registers its
  `IMessengerProvider` into on enable. The `MessengerService` and the inbound
  dispatcher resolve the *same* instance.
- **Command dispatcher** — collects `BotCommandProvider`s from the **enabled**
  plugin set (a disabled plugin contributes nothing — Liskov) and routes an
  inbound command / claimed free text to the owning consumer's `handle_action`.
- **Conversation mode** — tracks the active conversation owner per chat with an
  idle timeout, so free text falls back to the help menu once a chat goes idle.
- **One-time identity linking** — issues + redeems short-lived link tokens (D3)
  so an external messenger account can be bound to a vbwd user.

## Config keys (`config.json` / `admin-config.json`)

| Key | Default | Purpose |
| --- | --- | --- |
| `debug_mode` | `false` | Verbose debug logging for the bot-base plugin. Disable in production. |
| `link_token_ttl_seconds` | `900` | How long an issued one-time link token stays redeemable (D3). 60–86400. |
| `conversation_idle_timeout_seconds` | `1800` | How long a chat's active conversation owner persists without activity before it is treated as cleared. 60–86400. |

## How it fits the bot stack

```
bot-base          this plugin: the transport-neutral bot core
  ├─ bot-meinchat       a meinchat IMessengerProvider adapter
  ├─ bot-telegram       a Telegram IMessengerProvider adapter
  └─ bot-meinchat-llm   a BotCommandProvider consumer (the LLM consultant)
```

Declared plugin dependencies: none. `on_enable` registers its repositories and
the singleton `MessengerProviderRegistry` / `MessengerService` into
`current_app.container`.

## Docs

- [`docs/overview.md`](docs/overview.md) — the seams at a glance.
- [`docs/developer/rich-messages.md`](docs/developer/rich-messages.md) — the
  rich-message building blocks.

## Importable artifacts

None — bot-base is a library and owns no CMS widget or importable entity. See
[`docs/import/README.md`](docs/import/README.md).

## Quality gate

```
cd vbwd-backend && bin/pre-commit-check.sh --plugin bot_base --full
```
