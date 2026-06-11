"""S45.0 — create the bot_base tables (link, session, link_token).

Three tables for the provider-neutral bot bridge:
  * ``bot_base_link`` — verified provider-account ↔ vbwd-user binding (D3).
  * ``bot_base_session`` — per-chat active conversation owner.
  * ``bot_base_link_token`` — one-time, short-lived deep-link tokens (D3).

Anchored on the core root revision ``vbwd_001`` — bot_base is a brand-new
plugin with no prior revision, and the core root is always present in every
deployment, so this resolves standalone without depending on any other plugin
([[project_migration_graph_fragmentation]]). Revision id ≤ 32 chars
([[feedback_plugin_migrations_in_plugin]]). Validated up → down → up.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260610_1000_create_bot_base"
down_revision = "vbwd_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_base_link",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "vbwd_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("vbwd_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bot_ref", sa.String(length=255), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "provider_id",
            "external_user_id",
            name="uq_bot_base_link_provider_external",
        ),
    )
    op.create_index(
        "ix_bot_base_link_provider_id", "bot_base_link", ["provider_id"]
    )
    op.create_index(
        "ix_bot_base_link_vbwd_user_id", "bot_base_link", ["vbwd_user_id"]
    )

    op.create_table(
        "bot_base_session",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("chat_ref", sa.String(length=255), nullable=False),
        sa.Column("active_plugin", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "provider_id",
            "chat_ref",
            name="uq_bot_base_session_provider_chat",
        ),
    )

    op.create_table(
        "bot_base_link_token",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column(
            "vbwd_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("vbwd_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("token", name="uq_bot_base_link_token_token"),
    )
    op.create_index(
        "ix_bot_base_link_token_token", "bot_base_link_token", ["token"]
    )
    op.create_index(
        "ix_bot_base_link_token_vbwd_user_id",
        "bot_base_link_token",
        ["vbwd_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bot_base_link_token_vbwd_user_id", "bot_base_link_token")
    op.drop_index("ix_bot_base_link_token_token", "bot_base_link_token")
    op.drop_table("bot_base_link_token")
    op.drop_table("bot_base_session")
    op.drop_index("ix_bot_base_link_vbwd_user_id", "bot_base_link")
    op.drop_index("ix_bot_base_link_provider_id", "bot_base_link")
    op.drop_table("bot_base_link")
