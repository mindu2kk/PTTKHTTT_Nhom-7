"""Selectable sizes with preserved aggregate demo inventory and historical orders."""

import re

import sqlalchemy as sa

from alembic import op

revision = "0008_product_sizes"
down_revision = "0007_menswear_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_sizes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.String(80),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("size", sa.String(3), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.Column("reserved", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("product_id", "size", name="uq_product_sizes_product_size"),
        sa.UniqueConstraint("id", "product_id", name="uq_product_sizes_identity"),
        sa.CheckConstraint("size IN ('S','M','L','XL','XXL','F')", name="ck_product_sizes_size"),
        sa.CheckConstraint(
            "stock_quantity >= reserved AND reserved >= 0", name="ck_product_sizes_stock"
        ),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("""
        SELECT v.product_id, v.size, i.on_hand, i.reserved
        FROM product_variants v JOIN seller_offers o ON o.variant_id=v.id
        JOIN inventory i ON i.offer_id=o.id ORDER BY v.product_id
    """)
    ).mappings()
    for row in rows:
        tokens = {"XXL" if t == "2XL" else t for t in re.split(r"[\s,;/|]+", row["size"].upper())}
        sizes = [s for s in ("S", "M", "L", "XL", "XXL", "F") if s in tokens] or ["F"]
        available = row["on_hand"] - row["reserved"]
        for index, size in enumerate(sizes):
            held = row["reserved"] if index == 0 else 0
            connection.execute(
                sa.text("""
                INSERT INTO product_sizes(product_id,size,stock_quantity,reserved)
                VALUES (:pid,:size,:stock,:held)
            """),
                {
                    "pid": row["product_id"],
                    "size": size,
                    "stock": held + available // len(sizes) + (index < available % len(sizes)),
                    "held": held,
                },
            )
    for table in ("cart_items", "stock_reservations", "order_items"):
        op.add_column(table, sa.Column("product_size_id", sa.Integer(), nullable=True))
    # Legacy carts default to the first declared size; historical orders stay unspecified.
    connection.execute(
        sa.text("""
        UPDATE cart_items c SET product_size_id=(
            SELECT min(id) FROM product_sizes s WHERE s.product_id=c.product_id)
    """)
    )
    connection.execute(
        sa.text("""
        UPDATE stock_reservations r SET product_size_id=(
            SELECT min(s.id) FROM product_sizes s
            JOIN seller_offers o ON o.product_id=s.product_id WHERE o.id=r.offer_id)
    """)
    )
    for table, old_pk, columns in (
        ("cart_items", "cart_items_pkey", ["user_id", "product_size_id"]),
        (
            "stock_reservations",
            "stock_reservations_pkey",
            ["order_id", "offer_id", "product_size_id"],
        ),
    ):
        op.alter_column(table, "product_size_id", nullable=False)
        op.drop_constraint(old_pk, table, type_="primary")
        op.create_primary_key(old_pk, table, columns)
    for table in ("cart_items", "order_items"):
        op.create_foreign_key(
            "fk_" + table + "_product_size",
            table,
            "product_sizes",
            ["product_size_id", "product_id"],
            ["id", "product_id"],
        )
    op.create_foreign_key(
        "fk_stock_reservations_product_size",
        "stock_reservations",
        "product_sizes",
        ["product_size_id"],
        ["id"],
    )
    op.add_column("order_items", sa.Column("size_snapshot", sa.String(3), nullable=True))


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(
        sa.text("""
        SELECT EXISTS(SELECT 1 FROM cart_items GROUP BY user_id,product_id HAVING count(*)>1)
        OR EXISTS(SELECT 1 FROM stock_reservations GROUP BY order_id,offer_id HAVING count(*)>1)
        OR EXISTS(SELECT 1 FROM order_items WHERE size_snapshot IS NOT NULL)
    """)
    ):
        raise RuntimeError(
            "Rollback refused: size selections exist. Restore the pre-migration backup instead."
        )
    op.drop_column("order_items", "size_snapshot")
    for table in ("cart_items", "order_items"):
        op.drop_constraint("fk_" + table + "_product_size", table, type_="foreignkey")
    op.drop_constraint(
        "fk_stock_reservations_product_size", "stock_reservations", type_="foreignkey"
    )
    for table, columns in (
        ("cart_items", ["user_id", "product_id"]),
        ("stock_reservations", ["order_id", "offer_id"]),
    ):
        op.drop_constraint(table + "_pkey", table, type_="primary")
        op.create_primary_key(table + "_pkey", table, columns)
    for table in ("cart_items", "stock_reservations", "order_items"):
        op.drop_column(table, "product_size_id")
    op.drop_table("product_sizes")
