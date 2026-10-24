"""Separate real-data demo catalog and multiple verified product photographs."""

import sqlalchemy as sa

from alembic import op

revision = "0005_real_catalog"
down_revision = "0004_commerce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    for constraint in inspector.get_check_constraints("products"):
        if "data_profile IN" in constraint["sqltext"] or "data_profile" in constraint["sqltext"]:
            op.drop_constraint(constraint["name"], "products", type_="check")
    op.create_check_constraint(
        "ck_products_profile",
        "products",
        "data_profile IN ('demo_seed','approved_public','real_demo')",
    )
    for constraint in inspector.get_unique_constraints("product_images"):
        if constraint["column_names"] == ["product_id"]:
            op.drop_constraint(constraint["name"], "product_images", type_="unique")
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])
    op.create_index(
        "uq_product_primary_image",
        "product_images",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary IS TRUE"),
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(
        sa.text("SELECT EXISTS(SELECT 1 FROM products WHERE data_profile='real_demo')")
    ):
        raise RuntimeError(
            "Export and explicitly remove real_demo rows before rollback; no automatic data loss"
        )
    if connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT product_id FROM product_images "
            "GROUP BY product_id HAVING count(*)>1)"
        )
    ):
        raise RuntimeError(
            "Export additional photographs before rollback; no automatic image deletion"
        )
    op.drop_index("uq_product_primary_image", "product_images")
    op.drop_index("ix_product_images_product_id", "product_images")
    op.create_unique_constraint("product_images_product_id_key", "product_images", ["product_id"])
    op.drop_constraint("ck_products_profile", "products", type_="check")
    op.create_check_constraint(
        "ck_products_profile", "products", "data_profile IN ('demo_seed','approved_public')"
    )
