# bot-base — rich messages (`BotReply.meta` + `BotChoice.hint`)

**Since:** S70 (2026-06-11). **Audience:** consumer plugins (e.g. `subscription` storefront, `chat`, `taro`) and messenger adapters (`bot_telegram`, `bot_meinchat`).

`bot-base` stays provider-neutral: a consumer returns a `BotReply`, and each adapter renders it for its transport. To let consumers send **structured, styleable content** (choice cards, a command menu, a cart) without knowing the transport, `BotReply` carries an optional, provider-neutral **`meta`** payload, and `BotChoice` carries an optional **`hint`**.

## Types (`plugins/bot_base/bot_base/types.py`)

```python
@dataclass(frozen=True)
class BotChoice:
    label: str
    action_data: str           # opaque, namespaced "<plugin>:<action>:<arg>"
    hint: str | None = None    # compact secondary label, e.g. "€29/mo"  (S70)

@dataclass(frozen=True)
class BotReply:
    text: str                  # ALWAYS set — the plain fallback for non-rich clients
    choices: list[BotChoice] = ()
    meta: dict | None = None   # provider-neutral structured payload {"kind": ...}  (S70)
```

**Liskov / back-compat:** `meta` and `hint` are optional and default to `None`. A consumer that sets neither, and an adapter that ignores them, behave exactly as before. `text` is **always** populated so a transport (or an old client) that can't render `meta` still shows something sensible — keep the numbered list / run-on text in `text` as the fallback.

## `meta.kind` vocabulary

`meta` is `{"kind": "<kind>", …}`. The kinds defined so far (adapters/clients render them; anything unknown falls back to `text`):

| kind | shape | meaning |
|---|---|---|
| `bot_choices` | `{ "kind":"bot_choices", "text"?: str, … }` + the reply's `choices` (each may carry `hint`) | tappable choice cards; optional `text` is a **clean prompt** shown instead of `text`'s numbered fallback on rich clients |
| `bot_menu` | `{ "kind":"bot_menu", "commands":[{"command","description"}] }` | a styled command list (e.g. the built-in `/help`); tapping a row resends the command |
| `bot_cart` | `{ "kind":"bot_cart", "items":[{"name","quantity","unit_price","line_total"}], "total", "currency" }` | a cart summary card; amounts are **server-formatted strings** (no client math) |

A **tap** comes back inbound as a normal message whose `meta` is `{"kind":"bot_action","action_data":"<opaque>"}` (and `body` = the chosen label / command). The dispatcher lifts `action_data` onto `BotInbound.action_data` and routes it to the owning consumer's `handle_action` by namespace (D7).

`action_data` is **opaque** to bot-base and the adapters — only the owning consumer interprets it, and it must never be trusted for identity or price (recompute server-side).

## Built-in `/help` → `bot_menu`

`UpdateDispatcher` emits `/help` as a `bot_menu` whose rows are the built-ins (`/hello /start /stop /help`) **plus** every command collected from enabled consumers via the `CommandRegistry` — no hard-coded plugin knowledge. The same rows render the `text` fallback (DRY).

## Emitting from a consumer (example)

```python
# a choice list with prices + a clean prompt
return self._reply(
    text="Choose a tarif plan:\n1. Starter 2. Pro 3. Business\nReply with the number.",  # fallback
    choices=[self._choice(label="Pro", action_data="subscription:plan:<id>", hint="€29/mo"), …],
    meta={"kind": "bot_choices", "text": "Choose a tarif plan:"},
)

# a cart card
return self._reply(text=plain_cart_text, meta={"kind": "bot_cart", "items": [...], "total": "64.00", "currency": "EUR"})
```

Consumers stay **optional-bridge** (D1): no hard `bot-base` dependency, the neutral types are imported lazily, and a consumer works with the bridge absent. See the consumer guides in each plugin.

## How adapters consume it

Each `IMessengerProvider` translates `BotReply` (incl. `meta`/`hint`) for its transport. `bot_meinchat` maps it to `meinchat_message.meta` and the fe-user renders cards/menu/cart (see `plugins/meinchat/docs/developer/bot-rich-rendering.md`). `bot_telegram` can render `bot_menu`/inline keyboards or fall back to `text`. An adapter that does nothing special still sends `text` — nothing breaks.
