"""BotChoice.url — the optional navigable public route on a choice.

A choice may carry a public fe ``url`` so a rich widget navigates to it on tap
instead of sending the choice's ``action_data`` back. The field is optional and
defaults to ``None`` so every existing choice is unchanged (Liskov).
"""
from plugins.bot_base.bot_base.types import BotChoice


def test_bot_choice_url_defaults_to_none() -> None:
    choice = BotChoice(label="Reveal", action_data="taro:reveal:1")

    assert choice.url is None


def test_bot_choice_carries_an_explicit_url() -> None:
    choice = BotChoice(
        label="Open page",
        action_data="search:open:shop_product:blue-shirt",
        url="/shop/product/blue-shirt",
    )

    assert choice.url == "/shop/product/blue-shirt"
    # The existing fields are unaffected by the new optional field.
    assert choice.label == "Open page"
    assert choice.action_data == "search:open:shop_product:blue-shirt"
    assert choice.hint is None
