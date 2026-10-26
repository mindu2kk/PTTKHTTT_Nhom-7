"""M1 relational schema. Add future business aggregates through new migrations."""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(80))
    license: Mapped[str] = mapped_column(String(80))
    rights_status: Mapped[str] = mapped_column(String(30))
    allowed_use: Mapped[str] = mapped_column(Text)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("rights_status IN ('demo','approved','unknown','restricted')"),
    )


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30))
    counts: Mapped[dict[str, Any]] = mapped_column(JSONB)
    errors: Mapped[list[Any]] = mapped_column(JSONB)


class SourceProduct(Base):
    __tablename__ = "source_products"
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    raw_hash: Mapped[str] = mapped_column(String(64))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id"), index=True)


class CategoryRow(Base):
    __tablename__ = "categories"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"), index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name_vi: Mapped[str] = mapped_column(String(200))
    level: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="false")
    __table_args__ = (
        CheckConstraint("level >= 0", name="ck_categories_level"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id"),
        CheckConstraint(
            "(level = 0 AND parent_id IS NULL) OR (level > 0 AND parent_id IS NOT NULL)"
        ),
    )


class ProductRow(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True)
    name_vi: Mapped[str] = mapped_column(String(250))
    original_name: Mapped[str] = mapped_column(String(250))
    description_vi: Mapped[str] = mapped_column(Text)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), index=True)
    brand_id: Mapped[str | None] = mapped_column(String(80))
    gender: Mapped[str | None] = mapped_column(String(30), index=True)
    publication_status: Mapped[str] = mapped_column(String(30))
    verification_status: Mapped[str] = mapped_column(String(30))
    data_profile: Mapped[str] = mapped_column(String(30))
    search_text_normalized: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("publication_status IN ('draft','published','archived')"),
        CheckConstraint("verification_status IN ('pending','verified','rejected')"),
        CheckConstraint(
            "data_profile IN ('demo_seed','approved_public','real_demo')",
            name="ck_products_profile",
        ),
        Index(
            "ix_products_publication", "publication_status", "verification_status", "category_id"
        ),
    )


class ProductSource(Base):
    __tablename__ = "product_sources"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(100))
    field_provenance: Mapped[dict[str, Any]] = mapped_column(JSONB)
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_id", "external_id"],
            ["source_products.source_id", "source_products.external_id"],
        ),
        Index("ix_product_sources_raw", "source_id", "external_id"),
    )


class ProductAttribute(Base):
    __tablename__ = "product_attributes"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), primary_key=True)
    attribute_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    canonical_value: Mapped[str] = mapped_column(String(100))
    display_value_vi: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[int] = mapped_column(Integer)
    review_status: Mapped[str] = mapped_column(String(30))
    provenance: Mapped[str] = mapped_column(String(100))
    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 100"),
        Index("ix_product_attributes_filter", "attribute_key", "canonical_value", "product_id"),
    )


class ProductImage(Base):
    __tablename__ = "product_images"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(180), index=True)
    sha256: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    license_status: Mapped[str] = mapped_column(String(30))
    is_primary: Mapped[bool] = mapped_column(Boolean)
    alt_vi: Mapped[str] = mapped_column(String(250))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    __table_args__ = (
        CheckConstraint("width > 0 AND height > 0"),
        CheckConstraint("sort_order >= 0", name="ck_product_images_sort_order"),
        Index(
            "uq_product_primary_image",
            "product_id",
            unique=True,
            postgresql_where=is_primary.is_(True),
        ),
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), unique=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True)
    size: Mapped[str] = mapped_column(String(30))
    color: Mapped[str] = mapped_column(String(40), index=True)
    option_values: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30))
    __table_args__ = (UniqueConstraint("id", "product_id"),)


class SellerOffer(Base):
    __tablename__ = "seller_offers"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), unique=True)
    variant_id: Mapped[str] = mapped_column(String(100), unique=True)
    seller_id: Mapped[str] = mapped_column(String(80))  # demo source, not authenticated seller
    price_vnd: Mapped[int] = mapped_column(BigInteger, index=True)
    price_kind: Mapped[str] = mapped_column(String(30))
    seller_verified: Mapped[bool] = mapped_column(Boolean)
    active: Mapped[bool] = mapped_column(Boolean)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(
            ["variant_id", "product_id"], ["product_variants.id", "product_variants.product_id"]
        ),
        CheckConstraint("price_vnd > 0"),
        CheckConstraint("price_kind IN ('demo','merchant_verified','source_historical')"),
    )


class Inventory(Base):
    __tablename__ = "inventory"
    offer_id: Mapped[str] = mapped_column(ForeignKey("seller_offers.id"), primary_key=True)
    on_hand: Mapped[int] = mapped_column(Integer)
    reserved: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand"),)


class ProductSize(Base):
    __tablename__ = "product_sizes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    size: Mapped[str] = mapped_column(String(3))
    stock_quantity: Mapped[int] = mapped_column(Integer)
    reserved: Mapped[int] = mapped_column(Integer, server_default="0")
    __table_args__ = (
        UniqueConstraint("product_id", "size", name="uq_product_sizes_product_size"),
        UniqueConstraint("id", "product_id", name="uq_product_sizes_identity"),
        CheckConstraint("size IN ('S','M','L','XL','XXL','F')", name="ck_product_sizes_size"),
        CheckConstraint(
            "stock_quantity >= reserved AND reserved >= 0", name="ck_product_sizes_stock"
        ),
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    email: Mapped[str] = mapped_column(String(250), unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean)
    history_opt_in: Mapped[bool] = mapped_column(Boolean, server_default="false")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    total_vnd: Mapped[int] = mapped_column(BigInteger)
    data_profile: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    address: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    idempotency_key: Mapped[str | None] = mapped_column(String(80))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = (
        CheckConstraint("total_vnd >= 0"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_orders_owner_key"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    name_snapshot: Mapped[str] = mapped_column(String(250))
    unit_price_vnd: Mapped[int] = mapped_column(BigInteger)
    quantity: Mapped[int] = mapped_column(Integer)
    product_size_id: Mapped[int | None] = mapped_column(Integer)
    size_snapshot: Mapped[str | None] = mapped_column(String(3))
    __table_args__ = (
        CheckConstraint("unit_price_vnd > 0 AND quantity > 0"),
        ForeignKeyConstraint(
            ["product_size_id", "product_id"],
            ["product_sizes.id", "product_sizes.product_id"],
            name="fk_order_items_product_size",
        ),
    )


class ImageEmbedding(Base):
    __tablename__ = "image_embeddings"
    image_id: Mapped[str] = mapped_column(ForeignKey("product_images.id"), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    model_revision: Mapped[str] = mapped_column(String(80), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float]] = mapped_column(Vector(512))
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), primary_key=True)
    __table_args__ = (CheckConstraint("role IN ('customer','seller','admin')"),)


class SellerProfile(Base):
    __tablename__ = "seller_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    approved: Mapped[bool] = mapped_column(Boolean, server_default="false")


class SessionRow(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class CartRow(Base):
    __tablename__ = "carts"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CartItem(Base):
    __tablename__ = "cart_items"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("carts.user_id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    product_size_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 99"),
        ForeignKeyConstraint(
            ["product_size_id", "product_id"],
            ["product_sizes.id", "product_sizes.product_id"],
            name="fk_cart_items_product_size",
        ),
    )


class StockReservation(Base):
    __tablename__ = "stock_reservations"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    offer_id: Mapped[str] = mapped_column(ForeignKey("seller_offers.id"), primary_key=True)
    product_size_id: Mapped[int] = mapped_column(ForeignKey("product_sizes.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    __table_args__ = (
        CheckConstraint("quantity > 0"),
        CheckConstraint("status IN ('held','released','consumed')"),
    )


class MockPayment(Base):
    __tablename__ = "mock_payments"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    __table_args__ = (
        CheckConstraint("method IN ('cod','mock')"),
        CheckConstraint("status IN ('pending','simulated_paid','cancelled')"),
    )


class Shipment(Base):
    __tablename__ = "shipments"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30))
    provider: Mapped[str] = mapped_column(String(40), server_default="local_demo")


class SearchQuery(Base):
    __tablename__ = "search_queries"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    raw_text: Mapped[str] = mapped_column(String(300))
    modality: Mapped[str] = mapped_column(String(20))
    normalized_text: Mapped[str | None] = mapped_column(String(300))
    encoder_version: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class SearchResultRow(Base):
    __tablename__ = "search_results"
    query_id: Mapped[str] = mapped_column(
        ForeignKey("search_queries.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), primary_key=True)
    rank: Mapped[int] = mapped_column(Integer)
    final_score: Mapped[float | None] = mapped_column(Float)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    preference_score: Mapped[float | None] = mapped_column(Float)
    explanation: Mapped[str | None] = mapped_column(String(1000))


class SearchFilterRow(Base):
    __tablename__ = "search_filters"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    query_id: Mapped[str] = mapped_column(
        ForeignKey("search_queries.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer)
    key: Mapped[str] = mapped_column(String(40))
    value: Mapped[str | int] = mapped_column(JSONB)
    origin: Mapped[str] = mapped_column(String(20))
    operator: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        CheckConstraint("kind IN ('hard','soft','relaxed')"),
        CheckConstraint("origin IN ('ui_selected','explicit_text','inferred')"),
        CheckConstraint("position >= 0 AND confidence BETWEEN 0 AND 1"),
        UniqueConstraint("query_id", "kind", "position", name="uq_search_filter_position"),
    )
