"""Google Calendar connections and session-managed Co-Pilot chat tables.

Revision ID: 20261111_0008
Revises: 20261111_0007
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0008"
down_revision: str | Sequence[str] | None = "20261111_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("oauth_states") as batch_op:
        batch_op.add_column(
            sa.Column(
                "flow_type",
                sa.String(length=32),
                nullable=False,
                server_default="login",
            )
        )
        batch_op.add_column(sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_oauth_states_user_id_users"),
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    op.create_table(
        "google_calendar_connections",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("google_email", sa.String(length=320), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_google_calendar_connections_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_google_calendar_connections")),
        sa.UniqueConstraint("user_id", name=op.f("uq_google_calendar_connections_user_id")),
    )
    op.create_index(
        op.f("ix_google_calendar_connections_user_id"),
        "google_calendar_connections",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "copilot_conversations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_copilot_conversations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_copilot_conversations")),
    )
    op.create_index(
        op.f("ix_copilot_conversations_user_id"),
        "copilot_conversations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_copilot_conversations_user_recent",
        "copilot_conversations",
        ["user_id", "last_message_at"],
        unique=False,
    )

    op.create_table(
        "copilot_messages",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("conversation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", sa.JSON(), nullable=False),
        sa.Column("approval_ids", sa.JSON(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["copilot_conversations.id"],
            name=op.f("fk_copilot_messages_conversation_id_copilot_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_copilot_messages_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_copilot_messages")),
    )
    op.create_index(
        "ix_copilot_messages_conv_created",
        "copilot_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_copilot_messages_conversation_id"),
        "copilot_messages",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_copilot_messages_user_id"),
        "copilot_messages",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_copilot_messages_user_id"), table_name="copilot_messages")
    op.drop_index(op.f("ix_copilot_messages_conversation_id"), table_name="copilot_messages")
    op.drop_index("ix_copilot_messages_conv_created", table_name="copilot_messages")
    op.drop_table("copilot_messages")

    op.drop_index("ix_copilot_conversations_user_recent", table_name="copilot_conversations")
    op.drop_index(op.f("ix_copilot_conversations_user_id"), table_name="copilot_conversations")
    op.drop_table("copilot_conversations")

    op.drop_index(
        op.f("ix_google_calendar_connections_user_id"),
        table_name="google_calendar_connections",
    )
    op.drop_table("google_calendar_connections")

    with op.batch_alter_table("oauth_states") as batch_op:
        batch_op.drop_constraint(op.f("fk_oauth_states_user_id_users"), type_="foreignkey")
        batch_op.drop_column("user_id")
        batch_op.drop_column("flow_type")
