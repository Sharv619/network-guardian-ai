"""add feedback, tld_reputation, temporal_patterns tables

Revision ID: b16a14dbc232
Revises: 001
Create Date: 2026-02-21 00:39:35.942288

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b16a14dbc232"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "temporal_patterns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hour_of_day", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("threat_count", sa.Integer(), nullable=False),
        sa.Column("avg_risk_score", sa.Float(), nullable=False),
        sa.Column("anomaly_rate", sa.Float(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_temporal_hour_day", "temporal_patterns", ["hour_of_day", "day_of_week"], unique=True
    )

    op.create_table(
        "tld_reputation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tld", sa.String(length=20), nullable=False),
        sa.Column("reputation_score", sa.Float(), nullable=False),
        sa.Column("threat_count", sa.Integer(), nullable=False),
        sa.Column("safe_count", sa.Integer(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tld"),
    )
    op.create_index("idx_tld_reputation_tld", "tld_reputation", ["tld"], unique=False)

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domain_id", sa.Integer(), nullable=False),
        sa.Column("feedback_type", sa.String(length=20), nullable=False),
        sa.Column("original_category", sa.String(length=50), nullable=False),
        sa.Column("original_risk_score", sa.String(length=20), nullable=False),
        sa.Column("corrected_category", sa.String(length=50), nullable=True),
        sa.Column("corrected_risk_score", sa.String(length=20), nullable=True),
        sa.Column("user_note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["domain_id"],
            ["domains.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_feedback_domain_id", "feedback", ["domain_id"], unique=False)
    op.create_index("idx_feedback_processed", "feedback", ["processed"], unique=False)
    op.create_index("idx_feedback_type", "feedback", ["feedback_type"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_feedback_type", table_name="feedback")
    op.drop_index("idx_feedback_processed", table_name="feedback")
    op.drop_index("idx_feedback_domain_id", table_name="feedback")
    op.drop_table("feedback")

    op.drop_index("idx_tld_reputation_tld", table_name="tld_reputation")
    op.drop_table("tld_reputation")

    op.drop_index("idx_temporal_hour_day", table_name="temporal_patterns")
    op.drop_table("temporal_patterns")
