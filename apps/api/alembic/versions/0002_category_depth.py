"""Allow deeper taxonomies while retaining the original three-level demo fixture."""

from alembic import op

revision = "0002_category_depth"
down_revision = "0001_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("categories_level_check", "categories", type_="check")
    op.create_check_constraint("ck_categories_level", "categories", "level >= 0")


def downgrade() -> None:
    # Reject rollback if deeper rows exist; never delete those rows silently.
    op.drop_constraint("ck_categories_level", "categories", type_="check")
    op.create_check_constraint("categories_level_check", "categories", "level BETWEEN 0 AND 2")
