"""Activate the reviewed 19-leaf menswear tree; preserve legacy catalog links."""

import sqlalchemy as sa

from alembic import op

revision = "0007_menswear_categories"
down_revision = "0006_search_trace"
branch_labels = None
depends_on = None

CATEGORIES = [
    {
        "id": "nam",
        "parent_id": None,
        "slug": "nam",
        "name_vi": "Thời trang nam",
        "level": 0,
        "sort_order": 0,
        "is_active": True,
    },
    {
        "id": "nam-ao",
        "parent_id": "nam",
        "slug": "nam-ao",
        "name_vi": "Áo",
        "level": 1,
        "sort_order": 0,
        "is_active": True,
    },
    {
        "id": "nam-ao-pull",
        "parent_id": "nam-ao",
        "slug": "nam-ao-pull",
        "name_vi": "Áo pull",
        "level": 2,
        "sort_order": 0,
        "is_active": True,
    },
    {
        "id": "nam-polo",
        "parent_id": "nam-ao",
        "slug": "nam-polo",
        "name_vi": "Polo",
        "level": 2,
        "sort_order": 1,
        "is_active": True,
    },
    {
        "id": "nam-ao-so-mi",
        "parent_id": "nam-ao",
        "slug": "nam-ao-so-mi",
        "name_vi": "Áo sơ mi",
        "level": 2,
        "sort_order": 2,
        "is_active": True,
    },
    {
        "id": "nam-tanktop",
        "parent_id": "nam-ao",
        "slug": "nam-tanktop",
        "name_vi": "Tanktop",
        "level": 2,
        "sort_order": 3,
        "is_active": True,
    },
    {
        "id": "nam-cardigan-khoac-nhe",
        "parent_id": "nam-ao",
        "slug": "nam-cardigan-khoac-nhe",
        "name_vi": "Cardigan & khoác nhẹ",
        "level": 2,
        "sort_order": 4,
        "is_active": True,
    },
    {
        "id": "nam-ao-ni-len",
        "parent_id": "nam-ao",
        "slug": "nam-ao-ni-len",
        "name_vi": "Áo nỉ & len",
        "level": 2,
        "sort_order": 5,
        "is_active": True,
    },
    {
        "id": "nam-ao-khoac",
        "parent_id": "nam-ao",
        "slug": "nam-ao-khoac",
        "name_vi": "Áo khoác",
        "level": 2,
        "sort_order": 6,
        "is_active": True,
    },
    {
        "id": "nam-quan",
        "parent_id": "nam",
        "slug": "nam-quan",
        "name_vi": "Quần",
        "level": 1,
        "sort_order": 1,
        "is_active": True,
    },
    {
        "id": "nam-quan-lung",
        "parent_id": "nam-quan",
        "slug": "nam-quan-lung",
        "name_vi": "Quần lửng",
        "level": 2,
        "sort_order": 0,
        "is_active": True,
    },
    {
        "id": "nam-quan-au-vai",
        "parent_id": "nam-quan",
        "slug": "nam-quan-au-vai",
        "name_vi": "Quần âu vải",
        "level": 2,
        "sort_order": 1,
        "is_active": True,
    },
    {
        "id": "nam-quan-khaki",
        "parent_id": "nam-quan",
        "slug": "nam-quan-khaki",
        "name_vi": "Quần khaki",
        "level": 2,
        "sort_order": 2,
        "is_active": True,
    },
    {
        "id": "nam-quan-jeans",
        "parent_id": "nam-quan",
        "slug": "nam-quan-jeans",
        "name_vi": "Quần jeans",
        "level": 2,
        "sort_order": 3,
        "is_active": True,
    },
    {
        "id": "nam-quan-ni",
        "parent_id": "nam-quan",
        "slug": "nam-quan-ni",
        "name_vi": "Quần nỉ",
        "level": 2,
        "sort_order": 4,
        "is_active": True,
    },
    {
        "id": "nam-phu-kien",
        "parent_id": "nam",
        "slug": "nam-phu-kien",
        "name_vi": "Phụ kiện",
        "level": 1,
        "sort_order": 2,
        "is_active": True,
    },
    {
        "id": "nam-vong-charm",
        "parent_id": "nam-phu-kien",
        "slug": "nam-vong-charm",
        "name_vi": "Vòng tay - vòng cổ - charm",
        "level": 2,
        "sort_order": 0,
        "is_active": True,
    },
    {
        "id": "nam-mu",
        "parent_id": "nam-phu-kien",
        "slug": "nam-mu",
        "name_vi": "Mũ",
        "level": 2,
        "sort_order": 1,
        "is_active": True,
    },
    {
        "id": "nam-balo-tui",
        "parent_id": "nam-phu-kien",
        "slug": "nam-balo-tui",
        "name_vi": "Balo - túi",
        "level": 2,
        "sort_order": 2,
        "is_active": True,
    },
    {
        "id": "nam-day-lung-xich",
        "parent_id": "nam-phu-kien",
        "slug": "nam-day-lung-xich",
        "name_vi": "Dây lưng - xích",
        "level": 2,
        "sort_order": 3,
        "is_active": True,
    },
    {
        "id": "nam-khan-gang-tay",
        "parent_id": "nam-phu-kien",
        "slug": "nam-khan-gang-tay",
        "name_vi": "Khăn - găng tay",
        "level": 2,
        "sort_order": 4,
        "is_active": True,
    },
    {
        "id": "nam-giay-tat",
        "parent_id": "nam-phu-kien",
        "slug": "nam-giay-tat",
        "name_vi": "Giày - tất",
        "level": 2,
        "sort_order": 5,
        "is_active": True,
    },
    {
        "id": "nam-kinh-mat",
        "parent_id": "nam-phu-kien",
        "slug": "nam-kinh-mat",
        "name_vi": "Kính mắt",
        "level": 2,
        "sort_order": 6,
        "is_active": True,
    },
]


def upgrade() -> None:
    # Existing rows stay addressable by orders/import provenance, but are not public.
    op.add_column(
        "categories",
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    table = sa.table("categories", *(sa.column(key) for key in CATEGORIES[0]))
    op.bulk_insert(table, CATEGORIES)


def downgrade() -> None:
    connection = op.get_bind()
    ids = tuple(row["id"] for row in CATEGORIES)
    categories = sa.table("categories", sa.column("id"), sa.column("parent_id"))
    products = sa.table("products", sa.column("category_id"))
    if connection.scalar(
        sa.select(sa.func.count()).select_from(products).where(products.c.category_id.in_(ids))
    ):
        raise RuntimeError("Hãy chuyển sản phẩm ra khỏi cây danh mục mới trước khi rollback.")
    if connection.scalar(
        sa.select(sa.func.count())
        .select_from(categories)
        .where(categories.c.parent_id.in_(ids), categories.c.id.not_in(ids))
    ):
        raise RuntimeError("Hãy chuyển danh mục con bổ sung trước khi rollback.")
    for level in (2, 1, 0):
        connection.execute(
            categories.delete().where(
                categories.c.id.in_([row["id"] for row in CATEGORIES if row["level"] == level])
            )
        )
    op.drop_column("categories", "is_active")
