"""Record interpreted searches without retaining uploaded media."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_search_trace"
down_revision = "0005_real_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("search_queries", sa.Column("normalized_text", sa.String(300), nullable=True))
    op.add_column("search_queries", sa.Column("encoder_version", sa.String(80), nullable=True))
    op.add_column("search_results", sa.Column("final_score", sa.Float(), nullable=True))
    op.add_column("search_results", sa.Column("relevance_score", sa.Float(), nullable=True))
    op.add_column("search_results", sa.Column("preference_score", sa.Float(), nullable=True))
    op.add_column("search_results", sa.Column("explanation", sa.String(1000), nullable=True))
    op.create_table(
        "search_filters",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("query_id", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("operator", sa.String(10), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["query_id"], ["search_queries.id"], ondelete="CASCADE"),
        sa.CheckConstraint("kind IN ('hard','soft','relaxed')"),
        sa.CheckConstraint("origin IN ('ui_selected','explicit_text','inferred')"),
        sa.CheckConstraint("position >= 0 AND confidence BETWEEN 0 AND 1"),
        sa.UniqueConstraint("query_id", "kind", "position", name="uq_search_filter_position"),
    )
    op.create_index("ix_search_filters_query_id", "search_filters", ["query_id"])


def downgrade() -> None:
    op.drop_index("ix_search_filters_query_id", "search_filters")
    op.drop_table("search_filters")
    op.drop_column("search_results", "explanation")
    op.drop_column("search_results", "final_score")
    op.drop_column("search_results", "preference_score")
    op.drop_column("search_results", "relevance_score")
    op.drop_column("search_queries", "encoder_version")
    op.drop_column("search_queries", "normalized_text")
