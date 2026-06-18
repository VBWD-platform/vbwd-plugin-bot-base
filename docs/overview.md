# bot-base — overview

`bot-base` is the transport-neutral core of the bot stack. It defines the
contracts and registries; adapters supply transport, consumers supply behaviour.

## The two extension seams

1. **`MessengerProviderRegistry`** — an adapter plugin registers an
   `IMessengerProvider` (how to send/receive on a given transport). The registry
   is a process-wide singleton placed on `current_app.container` in `on_enable`,
   so the `MessengerService` and the inbound dispatcher resolve the same
   instance. Adapters: `bot-meinchat`, `bot-telegram`.

2. **Command providers** — a consumer plugin structurally implements a command
   provider (a `bot_namespace` + `get_bot_commands()` + `handle_action()`). The
   `CommandRegistry` collects these from the **enabled** plugin set, so a
   disabled consumer contributes nothing (Liskov). Consumer: `bot-meinchat-llm`.

## Inbound flow

```
transport → IMessengerProvider → dispatcher → owning consumer.handle_action → BotReply → MessengerService → transport
```

## Conversation mode + identity linking

- **Conversation mode** tracks which consumer "owns" the current chat, with an
  idle timeout (`conversation_idle_timeout_seconds`); after idle, free text
  falls back to the help menu.
- **One-time link tokens** (`link_token_ttl_seconds`) bind an external messenger
  identity to a vbwd user for adapters that need it (Telegram). The meinchat
  adapter does not — a meinchat sender is already an authenticated vbwd user.

## Rich messages

See [`developer/rich-messages.md`](developer/rich-messages.md) for the rich
message building blocks (text, links, choices) shared across the stack.
