"""Keep explicit gallery order while preserving existing product images."""

import sqlalchemy as sa

from alembic import op

revision = "0009_product_image_order"
down_revision = "0008_product_sizes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_images", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0")
    )
    op.execute("""
        UPDATE product_images i SET sort_order=ranked.position
        FROM (SELECT id, (row_number() OVER (
            PARTITION BY product_id ORDER BY is_primary DESC, id
        )-1)::integer AS position FROM product_images) ranked
        WHERE i.id=ranked.id
    """)
    op.create_check_constraint("ck_product_images_sort_order", "product_images", "sort_order >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_product_images_sort_order", "product_images", type_="check")
    op.drop_column("product_images", "sort_order")
