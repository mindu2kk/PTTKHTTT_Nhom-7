"""initial_catalog

Revision ID: 0001_catalog
Revises:
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_catalog"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Database-scoped prerequisites. Keep extensions on downgrade: other schemas may use them.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("parent_id", sa.String(length=80), nullable=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name_vi", sa.String(length=200), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "(level = 0 AND parent_id IS NULL) OR (level > 0 AND parent_id IS NOT NULL)"
        ),
        sa.CheckConstraint("level BETWEEN 0 AND 2"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False)
    op.create_table(
        "data_sources",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("license", sa.String(length=80), nullable=False),
        sa.Column("rights_status", sa.String(length=30), nullable=False),
        sa.Column("allowed_use", sa.Text(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rights_status IN ('demo','approved','unknown','restricted')"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=250), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_import_batches_source_id"), "import_batches", ["source_id"], unique=False
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("total_vnd", sa.BigInteger(), nullable=False),
        sa.Column("data_profile", sa.String(length=30), nullable=False),
        sa.CheckConstraint("total_vnd >= 0"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)
    op.create_table(
        "products",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("name_vi", sa.String(length=250), nullable=False),
        sa.Column("original_name", sa.String(length=250), nullable=False),
        sa.Column("description_vi", sa.Text(), nullable=False),
        sa.Column("category_id", sa.String(length=80), nullable=False),
        sa.Column("brand_id", sa.String(length=80), nullable=True),
        sa.Column("gender", sa.String(length=30), nullable=True),
        sa.Column("publication_status", sa.String(length=30), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("data_profile", sa.String(length=30), nullable=False),
        sa.Column("search_text_normalized", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("data_profile IN ('demo_seed','approved_public')"),
        sa.CheckConstraint("publication_status IN ('draft','published','archived')"),
        sa.CheckConstraint("verification_status IN ('pending','verified','rejected')"),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"], unique=False)
    op.create_index(op.f("ix_products_gender"), "products", ["gender"], unique=False)
    op.create_index(
        "ix_products_publication",
        "products",
        ["publication_status", "verification_status", "category_id"],
        unique=False,
    )
    op.create_table(
        "order_items",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("order_id", sa.String(length=80), nullable=False),
        sa.Column("product_id", sa.String(length=80), nullable=False),
        sa.Column("name_snapshot", sa.String(length=250), nullable=False),
        sa.Column("unit_price_vnd", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("unit_price_vnd > 0 AND quantity > 0"),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_product_id"), "order_items", ["product_id"], unique=False)
    op.create_table(
        "product_attributes",
        sa.Column("product_id", sa.String(length=80), nullable=False),
        sa.Column("attribute_key", sa.String(length=40), nullable=False),
        sa.Column("canonical_value", sa.String(length=100), nullable=False),
        sa.Column("display_value_vi", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(length=30), nullable=False),
        sa.Column("provenance", sa.String(length=100), nullable=False),
        sa.CheckConstraint("confidence BETWEEN 0 AND 100"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("product_id", "attribute_key"),
    )
    op.create_index(
        "ix_product_attributes_filter",
        "product_attributes",
        ["attribute_key", "canonical_value", "product_id"],
        unique=False,
    )
    op.create_table(
        "product_images",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("product_id", sa.String(length=80), nullable=False),
        sa.Column("storage_key", sa.String(length=180), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("license_status", sa.String(length=30), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("alt_vi", sa.String(length=250), nullable=False),
        sa.CheckConstraint("width > 0 AND height > 0"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_table(
        "product_variants",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("product_id", sa.String(length=80), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("size", sa.String(length=30), nullable=False),
        sa.Column("color", sa.String(length=40), nullable=False),
        sa.Column("option_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "product_id"),
        sa.UniqueConstraint("product_id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index(op.f("ix_product_variants_color"), "product_variants", ["color"], unique=False)
    op.create_table(
        "source_products",
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_hash", sa.String(length=64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("batch_id", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["import_batches.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
        ),
        sa.PrimaryKeyConstraint("source_id", "external_id"),
    )
    op.create_index(
        op.f("ix_source_products_batch_id"), "source_products", ["batch_id"], unique=False
    )
    op.create_table(
        "product_sources",
        sa.Column("product_id", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("field_provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_id", "external_id"],
            ["source_products.source_id", "source_products.external_id"],
        ),
        sa.PrimaryKeyConstraint("product_id", "source_id"),
    )
    op.create_index(
        "ix_product_sources_raw", "product_sources", ["source_id", "external_id"], unique=False
    )
    op.create_table(
        "seller_offers",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("product_id", sa.String(length=80), nullable=False),
        sa.Column("variant_id", sa.String(length=100), nullable=False),
        sa.Column("seller_id", sa.String(length=80), nullable=False),
        sa.Column("price_vnd", sa.BigInteger(), nullable=False),
        sa.Column("price_kind", sa.String(length=30), nullable=False),
        sa.Column("seller_verified", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("price_kind IN ('demo','merchant_verified','source_historical')"),
        sa.CheckConstraint("price_vnd > 0"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["variant_id", "product_id"],
            ["product_variants.id", "product_variants.product_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id"),
        sa.UniqueConstraint("variant_id"),
    )
    op.create_index(
        op.f("ix_seller_offers_price_vnd"), "seller_offers", ["price_vnd"], unique=False
    )
    op.create_table(
        "inventory",
        sa.Column("offer_id", sa.String(length=100), nullable=False),
        sa.Column("on_hand", sa.Integer(), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand"),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["seller_offers.id"],
        ),
        sa.PrimaryKeyConstraint("offer_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("inventory")
    op.drop_index(op.f("ix_seller_offers_price_vnd"), table_name="seller_offers")
    op.drop_table("seller_offers")
    op.drop_index("ix_product_sources_raw", table_name="product_sources")
    op.drop_table("product_sources")
    op.drop_index(op.f("ix_source_products_batch_id"), table_name="source_products")
    op.drop_table("source_products")
    op.drop_index(op.f("ix_product_variants_color"), table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_table("product_images")
    op.drop_index("ix_product_attributes_filter", table_name="product_attributes")
    op.drop_table("product_attributes")
    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_products_publication", table_name="products")
    op.drop_index(op.f("ix_products_gender"), table_name="products")
    op.drop_index(op.f("ix_products_category_id"), table_name="products")
    op.drop_table("products")
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_index(op.f("ix_import_batches_source_id"), table_name="import_batches")
    op.drop_table("import_batches")
    op.drop_table("users")
    op.drop_table("data_sources")
    op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")
    op.drop_table("categories")
    # ### end Alembic commands ###
