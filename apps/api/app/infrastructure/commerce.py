import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.query_parser import normalize
from app.domain.commerce import Actor, BusinessError
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.models import (
    CartItem,
    CartRow,
    CategoryRow,
    DataSource,
    ImportBatch,
    Inventory,
    MockPayment,
    Order,
    OrderItem,
    ProductAttribute,
    ProductImage,
    ProductRow,
    ProductSource,
    ProductVariant,
    SearchQuery,
    SearchResultRow,
    SellerOffer,
    SellerProfile,
    SessionRow,
    Shipment,
    SourceProduct,
    StockReservation,
    User,
    UserRole,
)


def uid() -> str:
    return uuid.uuid4().hex


class SqlCommerceStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession], profile: str):
        self.factory, self.profile = factory, profile

    async def maintenance(self) -> None:
        async with self.factory.begin() as s:
            await s.execute(delete(SessionRow).where(SessionRow.expires_at < datetime.now(UTC)))
            await s.execute(
                delete(SearchQuery).where(
                    SearchQuery.created_at < datetime.now(UTC) - timedelta(days=7)
                )
            )

    async def _actor(self, session: AsyncSession, user: User) -> Actor:
        roles = tuple(
            (await session.scalars(select(UserRole.role).where(UserRole.user_id == user.id))).all()
        )
        return Actor(user.id, user.email, roles, user.history_opt_in)

    async def register(self, email: str, password_hash: str) -> Actor:
        try:
            async with self.factory.begin() as s:
                user = User(
                    id=uid(),
                    email=email,
                    password_hash=password_hash,
                    is_active=True,
                    history_opt_in=False,
                )
                s.add(user)
                await s.flush()
                s.add(UserRole(user_id=user.id, role="customer"))
                return Actor(user.id, email, ("customer",), False)
        except IntegrityError as error:
            raise BusinessError(
                409, "Không thể đăng ký email này. Hãy đăng nhập hoặc dùng email khác."
            ) from error

    async def credentials(self, email: str) -> tuple[Actor, str | None] | None:
        async with self.factory() as s:
            user = await s.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
            return (await self._actor(s, user), user.password_hash) if user else None

    async def session(self, token_hash: str) -> Actor | None:
        async with self.factory() as s:
            user = await s.scalar(
                select(User)
                .join(SessionRow, SessionRow.user_id == User.id)
                .where(
                    SessionRow.token_hash == token_hash,
                    SessionRow.expires_at > datetime.now(UTC),
                    User.is_active.is_(True),
                )
            )
            return await self._actor(s, user) if user else None

    async def start_session(self, user_id: str, token_hash: str) -> None:
        async with self.factory.begin() as s:
            await s.scalar(select(User).where(User.id == user_id).with_for_update())
            await s.execute(delete(SessionRow).where(SessionRow.expires_at < datetime.now(UTC)))
            # Bound each user's active sessions, oldest first.
            old = (
                await s.scalars(
                    select(SessionRow.token_hash)
                    .where(SessionRow.user_id == user_id)
                    .order_by(SessionRow.expires_at.desc())
                    .offset(4)
                )
            ).all()
            if old:
                await s.execute(delete(SessionRow).where(SessionRow.token_hash.in_(old)))
            s.add(
                SessionRow(
                    token_hash=token_hash,
                    user_id=user_id,
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                )
            )

    async def end_session(self, token_hash: str) -> None:
        async with self.factory.begin() as s:
            await s.execute(delete(SessionRow).where(SessionRow.token_hash == token_hash))

    async def cart(self, actor: Actor, lines: list[dict[str, Any]] | None) -> dict[str, Any]:
        async with self.factory.begin() as s:
            await s.scalar(select(User).where(User.id == actor.id).with_for_update())
            if lines is not None:
                await s.execute(insert(CartRow).values(user_id=actor.id).on_conflict_do_nothing())
                await s.execute(delete(CartItem).where(CartItem.user_id == actor.id))
                for line in lines:
                    if not await SqlCatalogRepository(s, self.profile).get_product(
                        line["product_id"]
                    ):
                        raise BusinessError(
                            409, "Một sản phẩm không còn khả dụng. Hãy kiểm tra giỏ hàng."
                        )
                    s.add(
                        CartItem(
                            user_id=actor.id,
                            product_id=line["product_id"],
                            quantity=line["quantity"],
                        )
                    )
                await s.flush()
            stored = (
                await s.scalars(
                    select(CartItem)
                    .where(CartItem.user_id == actor.id)
                    .order_by(CartItem.product_id)
                )
            ).all()
            result: list[dict[str, Any]] = []
            for row in stored:
                product = await SqlCatalogRepository(s, self.profile).get_product(row.product_id)
                result.append(
                    {
                        "product_id": row.product_id,
                        "quantity": row.quantity,
                        "price_vnd": product.price_vnd if product else None,
                        "available_quantity": product.available_quantity if product else 0,
                    }
                )
            return {
                "items": result,
                "total_vnd": sum((r["price_vnd"] or 0) * r["quantity"] for r in result),
            }

    async def _order(self, s: AsyncSession, row: Order) -> dict[str, Any]:
        items = (
            await s.scalars(
                select(OrderItem).where(OrderItem.order_id == row.id).order_by(OrderItem.id)
            )
        ).all()
        payment = await s.get(MockPayment, row.id)
        shipment = await s.get(Shipment, row.id)
        return {
            "code": row.code,
            "status": row.status,
            "total_vnd": row.total_vnd,
            "created_at": row.created_at.isoformat(),
            "data_profile": row.data_profile,
            "address": row.address,
            "payment_method": payment.method if payment else "cod",
            "payment_status": payment.status if payment else "pending",
            "shipment_status": shipment.status if shipment else "not_started",
            "items": [
                {
                    "product_id": i.product_id,
                    "name": i.name_snapshot,
                    "unit_price_vnd": i.unit_price_vnd,
                    "quantity": i.quantity,
                }
                for i in items
            ],
        }

    async def checkout(self, actor: Actor, key: str, payload: dict[str, Any]) -> dict[str, Any]:
        hashed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        async with self.factory.begin() as s:
            # Per-owner lock serializes retries; inventory locks in stable order serialize buyers.
            await s.scalar(select(User).where(User.id == actor.id).with_for_update())
            old = await s.scalar(
                select(Order).where(Order.user_id == actor.id, Order.idempotency_key == key)
            )
            if old:
                if old.request_hash != hashed:
                    raise BusinessError(409, "Mã yêu cầu đã dùng với nội dung khác.")
                return await self._order(s, old)
            selected = []
            for line in sorted(payload["items"], key=lambda x: x["product_id"]):
                offer = await s.scalar(
                    select(SellerOffer)
                    .where(SellerOffer.product_id == line["product_id"])
                    .with_for_update()
                )
                stock = (
                    await s.scalar(
                        select(Inventory).where(Inventory.offer_id == offer.id).with_for_update()
                    )
                    if offer
                    else None
                )
                product = await SqlCatalogRepository(s, self.profile).get_product(
                    line["product_id"]
                )
                if (
                    not offer
                    or not stock
                    or not product
                    or product.price_vnd != line["expected_price_vnd"]
                    or stock.on_hand - stock.reserved < line["quantity"]
                ):
                    raise BusinessError(
                        409, "Giá hoặc tồn kho đã thay đổi. Hãy kiểm tra lại giỏ hàng."
                    )
                selected.append((line, offer, stock, product))
            row = Order(
                id=uid(),
                code="HM" + uuid.uuid4().hex[:14].upper(),
                user_id=actor.id,
                status="CONFIRMED",
                total_vnd=sum(
                    line["quantity"] * product.price_vnd for line, offer, stock, product in selected
                ),
                data_profile=self.profile,
                address=payload["address"],
                idempotency_key=key,
                request_hash=hashed,
            )
            s.add(row)
            await s.flush()
            for line, offer, stock, product in selected:
                stock.reserved += line["quantity"]
                stock.version += 1
                stock.updated_at = datetime.now(UTC)
                s.add(
                    OrderItem(
                        id=uid(),
                        order_id=row.id,
                        product_id=product.id,
                        name_snapshot=product.name_vi,
                        unit_price_vnd=product.price_vnd,
                        quantity=line["quantity"],
                    )
                )
                s.add(
                    StockReservation(
                        order_id=row.id, offer_id=offer.id, quantity=line["quantity"], status="held"
                    )
                )
            s.add(
                MockPayment(
                    order_id=row.id,
                    method=payload["method"],
                    status="simulated_paid" if payload["method"] == "mock" else "pending",
                )
            )
            s.add(Shipment(order_id=row.id, status="not_started", provider="local_demo"))
            await s.execute(delete(CartItem).where(CartItem.user_id == actor.id))
            await s.flush()
            return await self._order(s, row)

    async def orders(self, actor: Actor, code: str | None = None) -> list[dict[str, Any]]:
        async with self.factory() as s:
            query = select(Order).where(Order.user_id == actor.id)
            if code is not None:
                query = query.where(Order.code == code)
            rows = (
                await s.scalars(query.order_by(Order.created_at.desc(), Order.id).limit(100))
            ).all()
            return [await self._order(s, row) for row in rows]

    async def transition(self, actor: Actor, code: str, status: str) -> dict[str, Any]:
        async with self.factory.begin() as s:
            row = await s.scalar(select(Order).where(Order.code == code).with_for_update())
            if not row or (row.user_id != actor.id and "admin" not in actor.roles):
                raise BusinessError(404, "Không tìm thấy đơn hàng của bạn.")
            if row.status == status:
                return await self._order(s, row)
            if status == "CANCELLED":
                if row.status not in {"CONFIRMED", "PACKING"}:
                    raise BusinessError(409, "Đơn đã giao đi, không thể hủy.")
            elif "admin" not in actor.roles:
                raise BusinessError(403, "Bạn không có quyền cập nhật trạng thái này.")
            elif {"CONFIRMED": "PACKING", "PACKING": "SHIPPED", "SHIPPED": "DELIVERED"}.get(
                row.status
            ) != status:
                raise BusinessError(409, "Thứ tự trạng thái không hợp lệ.")
            reservations = (
                await s.scalars(
                    select(StockReservation)
                    .where(StockReservation.order_id == row.id)
                    .order_by(StockReservation.offer_id)
                )
            ).all()
            for reserve in reservations:
                if reserve.status != "held" or status not in {"CANCELLED", "SHIPPED"}:
                    continue
                stock = await s.scalar(
                    select(Inventory)
                    .where(Inventory.offer_id == reserve.offer_id)
                    .with_for_update()
                )
                if stock is None:
                    raise BusinessError(409, "Không thể cập nhật tồn kho.")
                stock.reserved -= reserve.quantity
                if status == "SHIPPED":
                    stock.on_hand -= reserve.quantity
                stock.version += 1
                reserve.status = "released" if status == "CANCELLED" else "consumed"
            row.status = status
            payment = await s.get(MockPayment, row.id)
            shipment = await s.get(Shipment, row.id)
            if payment and status == "CANCELLED":
                payment.status = "cancelled"
            if shipment:
                shipment.status = status.lower()
            await s.flush()
            return await self._order(s, row)

    async def history(self, actor: Actor, action: str) -> list[dict[str, Any]]:
        async with self.factory.begin() as s:
            await s.execute(
                delete(SearchQuery).where(
                    SearchQuery.created_at < datetime.now(UTC) - timedelta(days=7)
                )
            )
            user = await s.scalar(select(User).where(User.id == actor.id).with_for_update())
            if user is None:
                return []
            if action in {"enable", "disable"}:
                user.history_opt_in = action == "enable"
            if action in {"disable", "delete"}:
                await s.execute(delete(SearchQuery).where(SearchQuery.user_id == actor.id))
            rows = (
                await s.scalars(
                    select(SearchQuery)
                    .where(SearchQuery.user_id == actor.id)
                    .order_by(SearchQuery.created_at.desc())
                    .limit(100)
                )
            ).all()
            return [
                {
                    "id": r.id,
                    "text": r.raw_text,
                    "modality": r.modality,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]

    async def remember(self, actor: Actor, text: str, modality: str, products: list[str]) -> None:
        async with self.factory.begin() as s:
            user = await s.scalar(select(User).where(User.id == actor.id).with_for_update())
            if not user or not user.history_opt_in:
                return
            cutoff = datetime.now(UTC) - timedelta(days=7)
            await s.execute(delete(SearchQuery).where(SearchQuery.created_at < cutoff))
            old = (
                await s.scalars(
                    select(SearchQuery.id)
                    .where(SearchQuery.user_id == actor.id)
                    .order_by(SearchQuery.created_at.desc(), SearchQuery.id)
                    .offset(99)
                )
            ).all()
            if old:
                await s.execute(delete(SearchQuery).where(SearchQuery.id.in_(old)))
            query = SearchQuery(id=uid(), user_id=actor.id, raw_text=text[:300], modality=modality)
            s.add(query)
            await s.flush()
            for rank, pid in enumerate(dict.fromkeys(products[:24]), 1):
                s.add(SearchResultRow(query_id=query.id, product_id=pid, rank=rank))

    async def manage(self, actor: Actor, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not {"admin", "seller"}.intersection(actor.roles):
            raise BusinessError(403, "Bạn không có quyền quản lý sản phẩm.")
        if self.profile == "real_demo" and action not in {"list", "images"}:
            raise BusinessError(
                409,
                "Danh mục ảnh thật được nhập có kiểm duyệt; biểu mẫu chỉnh sửa chưa được hỗ trợ.",
            )
        admin = "admin" in actor.roles
        async with self.factory.begin() as s:
            if action in {"create", "import"}:
                await s.scalar(select(User).where(User.id == actor.id).with_for_update())
            if action == "images":
                images = (
                    await s.scalars(
                        select(ProductImage)
                        .join(ProductRow, ProductRow.id == ProductImage.product_id)
                        .where(
                            ProductImage.license_status
                            == ("demo" if self.profile == "demo_seed" else "approved"),
                            ProductRow.data_profile == self.profile,
                        )
                        .order_by(ProductImage.id)
                        .limit(100)
                    )
                ).all()
                return {
                    "items": [
                        {"id": image.id, "url": image.storage_key, "alt": image.alt_vi}
                        for image in images
                    ]
                }
            if action in {"preview_import", "import"}:
                if not admin:
                    raise BusinessError(403, "Chỉ quản trị viên được nhập danh mục.")
                errors = []
                for index, record in enumerate(payload["records"], 1):
                    if not await s.get(CategoryRow, record["category_id"]):
                        errors.append(
                            {
                                "row": index,
                                "field": "category_id",
                                "message": "Danh mục không tồn tại.",
                            }
                        )
                    image = await s.get(ProductImage, record["image_id"])
                    if not image or image.license_status != "demo":
                        errors.append(
                            {
                                "row": index,
                                "field": "image_id",
                                "message": "Ảnh chưa có quyền sử dụng mô phỏng.",
                            }
                        )
                preview = {
                    "rows": len(payload["records"]),
                    "errors": errors,
                    "publish_status": "draft_pending_review",
                }
                if action == "preview_import":
                    return preview
                if errors:
                    raise BusinessError(422, "Đợt nhập có lỗi. Hãy sửa và xem trước lại.")
                created = [await self._create(s, actor, record) for record in payload["records"]]
                return {**preview, "created": created}
            if action == "list":
                query = (
                    select(ProductRow, SellerOffer)
                    .join(SellerOffer, SellerOffer.product_id == ProductRow.id)
                    .where(ProductRow.data_profile == self.profile)
                )
                if not admin:
                    query = query.where(SellerOffer.seller_id == actor.id)
                rows = (
                    await s.execute(
                        query.order_by(ProductRow.updated_at.desc(), ProductRow.id).limit(100)
                    )
                ).all()
                batches = (
                    (
                        await s.scalars(
                            select(ImportBatch).order_by(ImportBatch.started_at.desc()).limit(20)
                        )
                    ).all()
                    if admin
                    else []
                )
                return {
                    "items": [
                        {
                            "id": p.id,
                            "name": p.name_vi,
                            "category_id": p.category_id,
                            "status": p.publication_status,
                            "review": p.verification_status,
                            "price_vnd": o.price_vnd,
                            "seller_id": o.seller_id,
                        }
                        for p, o in rows
                    ],
                    "read_only": self.profile == "real_demo",
                    "batches": [
                        {"id": b.id, "status": b.status, "counts": b.counts, "errors": b.errors}
                        for b in batches
                    ],
                }
            if action == "create":
                profile = await s.get(SellerProfile, actor.id)
                if not admin and (not profile or not profile.approved):
                    raise BusinessError(403, "Hồ sơ người bán chưa được duyệt.")
                return await self._create(s, actor, payload)
            product = await s.scalar(
                select(ProductRow).where(ProductRow.id == payload["id"]).with_for_update()
            )
            offer = await s.scalar(
                select(SellerOffer).where(SellerOffer.product_id == payload["id"]).with_for_update()
            )
            if not product or not offer or (not admin and offer.seller_id != actor.id):
                raise BusinessError(404, "Không tìm thấy sản phẩm quản lý.")
            if action == "publish":
                if not admin:
                    raise BusinessError(403, "Chỉ quản trị viên được duyệt xuất bản.")
                image = await s.scalar(
                    select(ProductImage).where(
                        ProductImage.product_id == product.id, ProductImage.is_primary.is_(True)
                    )
                )
                sources = (
                    await s.scalars(
                        select(DataSource.rights_status)
                        .join(ProductSource, ProductSource.source_id == DataSource.id)
                        .where(ProductSource.product_id == product.id)
                    )
                ).all()
                allowed = "demo" if self.profile == "demo_seed" else "approved"
                if (
                    not image
                    or image.license_status != allowed
                    or not sources
                    or any(x != allowed for x in sources)
                ):
                    raise BusinessError(409, "Chưa đủ quyền nguồn dữ liệu hoặc ảnh để xuất bản.")
                product.publication_status = "published"
                product.verification_status = "verified"
                offer.seller_verified = True
            elif action == "archive":
                product.publication_status = "archived"
            elif action == "update":
                stock = await s.scalar(
                    select(Inventory).where(Inventory.offer_id == offer.id).with_for_update()
                )
                if not stock or payload["stock"] < stock.reserved:
                    raise BusinessError(409, "Tồn kho không được thấp hơn số lượng đang giữ.")
                stock.on_hand = payload["stock"]
                stock.version += 1
                offer.price_vnd = payload["price_vnd"]
                # Seller edits require another independent review.
                if not admin:
                    product.publication_status = "draft"
                    product.verification_status = "pending"
            else:
                raise BusinessError(422, "Thao tác không hợp lệ.")
            product.updated_at = datetime.now(UTC)
            if action in {"publish", "archive"}:
                raw = await s.scalar(
                    select(SourceProduct)
                    .join(
                        ProductSource,
                        (ProductSource.source_id == SourceProduct.source_id)
                        & (ProductSource.external_id == SourceProduct.external_id),
                    )
                    .where(
                        ProductSource.product_id == product.id,
                        SourceProduct.source_id == "operator-" + offer.seller_id,
                    )
                )
                if raw:
                    batch = await s.get(ImportBatch, raw.batch_id)
                    if batch:
                        batch.status = "approved" if action == "publish" else "archived"
            return {
                "id": product.id,
                "status": product.publication_status,
                "review": product.verification_status,
            }

    async def _create(self, s: AsyncSession, actor: Actor, p: dict[str, Any]) -> dict[str, Any]:
        if self.profile != "demo_seed" or not p.get("original_data_confirmed"):
            raise BusinessError(
                422, "Chỉ tạo dữ liệu mô phỏng do bạn có quyền sử dụng trong chế độ này."
            )
        if not await s.get(CategoryRow, p["category_id"]):
            raise BusinessError(422, "Danh mục không tồn tại.")
        image = await s.scalar(
            select(ProductImage).where(
                ProductImage.id == p["image_id"], ProductImage.license_status == "demo"
            )
        )
        if not image:
            raise BusinessError(422, "Hãy chọn ảnh minh họa gốc đã được duyệt.")
        pid = "demo-" + uid()
        source = "operator-" + actor.id
        batch = uid()
        now = datetime.now(UTC)
        raw = json.dumps(p, sort_keys=True, ensure_ascii=False)
        raw_hash = hashlib.sha256(raw.encode()).hexdigest()
        old = await s.scalar(
            select(SourceProduct).where(
                SourceProduct.source_id == source, SourceProduct.raw_hash == raw_hash
            )
        )
        if old:
            product = await s.get(ProductRow, old.external_id)
            if product:
                return {
                    "id": product.id,
                    "batch_id": old.batch_id,
                    "status": product.publication_status,
                    "review": product.verification_status,
                    "reused": True,
                }
        await s.execute(
            insert(DataSource)
            .values(
                id=source,
                name="Dữ liệu mô phỏng của người vận hành",
                version="1",
                license="CC0-1.0",
                rights_status="demo",
                allowed_use="Original demo data explicitly affirmed by operator",
                last_checked_at=now,
            )
            .on_conflict_do_nothing()
        )
        s.add(
            ImportBatch(
                id=batch,
                source_id=source,
                started_at=now,
                status="pending_review",
                counts={"created": 1},
                errors=[],
            )
        )
        await s.flush()
        s.add(
            SourceProduct(
                source_id=source,
                external_id=pid,
                raw_json=p,
                raw_hash=raw_hash,
                imported_at=now,
                batch_id=batch,
            )
        )
        s.add(
            ProductRow(
                id=pid,
                slug=pid,
                name_vi=p["name"],
                original_name=p["name"],
                description_vi=p["description"],
                category_id=p["category_id"],
                brand_id=None,
                gender=None,
                publication_status="draft",
                verification_status="pending",
                data_profile="demo_seed",
                search_text_normalized=normalize(p["name"] + " " + p["description"]),
            )
        )
        await s.flush()
        s.add(
            ProductSource(
                product_id=pid,
                source_id=source,
                external_id=pid,
                field_provenance={"all": "operator-original"},
            )
        )
        s.add(
            ProductImage(
                id="image-" + pid,
                product_id=pid,
                storage_key=image.storage_key,
                sha256=image.sha256,
                width=image.width,
                height=image.height,
                license_status="demo",
                is_primary=True,
                alt_vi=p["name"],
            )
        )
        # Products can explicitly reuse approved original illustration bytes.
        s.add(
            ProductVariant(
                id="variant-" + pid,
                product_id=pid,
                sku=pid,
                size=p["size"],
                color=p["color"],
                option_values={},
                status="active",
            )
        )
        s.add(
            ProductAttribute(
                product_id=pid,
                attribute_key="material",
                canonical_value=normalize(p["material"]),
                display_value_vi=p["material"],
                confidence=100,
                review_status="verified",
                provenance="operator-original",
            )
        )
        await s.flush()
        s.add(
            SellerOffer(
                id="offer-" + pid,
                product_id=pid,
                variant_id="variant-" + pid,
                seller_id=actor.id,
                price_vnd=p["price_vnd"],
                price_kind="demo",
                seller_verified=False,
                active=True,
            )
        )
        await s.flush()
        s.add(Inventory(offer_id="offer-" + pid, on_hand=p["stock"], reserved=0, version=1))
        return {"id": pid, "batch_id": batch, "status": "draft", "review": "pending"}
