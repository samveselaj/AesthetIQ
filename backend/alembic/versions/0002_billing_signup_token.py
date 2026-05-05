"""billing fields + signup_tokens

Revision ID: 0002_billing_signup_token
Revises: 0001_initial
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_billing_signup_token"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("lemon_subscription_id", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_organizations_lemon_subscription_id",
        "organizations",
        ["lemon_subscription_id"],
    )
    op.add_column(
        "organizations",
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "signup_tokens",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, index=True),
        sa.Column("token", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lemon_subscription_id", sa.String(length=64), nullable=True),
        sa.Column("plan", sa.String(length=32), nullable=False, server_default="starter"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("signup_tokens")
    op.drop_constraint(
        "uq_organizations_lemon_subscription_id", "organizations", type_="unique"
    )
    op.drop_column("organizations", "trial_ends_at")
    op.drop_column("organizations", "lemon_subscription_id")
