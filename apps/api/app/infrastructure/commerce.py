import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.query_parser import normalize
from app.domain.commerce import Actor, BusinessError
from app.domain.search import SearchRecord
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.models import (
    CartItem,
    CartRow,
    CategoryRow,
    DataSource,
    ImageEmbedding,
    ImportBatch,
    Inventory,
    MockPayment,
    Order,
    OrderItem,
    ProductAttribute,
    ProductImage,
    ProductRow,
    ProductSize,
    ProductSource,
    ProductVariant,
    SearchFilterRow,
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
from app.infrastructure.product_image_url import inspect_image, validate_image_url
from app.infrastructure.sizes import initialize_sizes


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

    async def _size(self, s: AsyncSession, product_id: str, size_id: int | None) -> ProductSize:
        query = select(ProductSize).where(ProductSize.product_id == product_id)
        if size_id is not None:
            query = query.where(ProductSize.id == size_id)
        sizes = (await s.scalars(query.order_by(ProductSize.id).with_for_update())).all()
        if len(sizes) != 1:
            raise BusinessError(409, "Hãy chọn size còn hàng của sản phẩm.")
        return sizes[0]

    async def cart(self, actor: Actor, lines: list[dict[str, Any]] | None) -> dict[str, Any]:
        async with self.factory.begin() as s:
            await s.scalar(select(User).where(User.id == actor.id).with_for_update())
            if lines is not None:
                await s.execute(insert(CartRow).values(user_id=actor.id).on_conflict_do_nothing())
                await s.execute(delete(CartItem).where(CartItem.user_id == actor.id))
                seen: set[int] = set()
                for line in sorted(
                    lines, key=lambda x: (x["product_id"], x.get("product_size_id") or 0)
                ):
                    size = await self._size(s, line["product_id"], line.get("product_size_id"))
                    if size.id in seen:
                        raise BusinessError(422, "Sản phẩm và size bị trùng.")
                    seen.add(size.id)
                    product = await SqlCatalogRepository(s, self.profile).get_product(
                        line["product_id"]
                    )
                    if (
                        not product
                        or min(product.available_quantity, size.stock_quantity - size.reserved)
                        < line["quantity"]
                    ):
                        raise BusinessError(
                            409, "Một sản phẩm không còn khả dụng. Hãy kiểm tra giỏ hàng."
                        )
                    s.add(
                        CartItem(
                            user_id=actor.id,
                            product_id=line["product_id"],
                            product_size_id=size.id,
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
                stored_size = await s.get(ProductSize, row.product_size_id)
                result.append(
                    {
                        "product_id": row.product_id,
                        "product_size_id": row.product_size_id,
                        "size": stored_size.size if stored_size else None,
                        "quantity": row.quantity,
                        "price_vnd": product.price_vnd if product else None,
                        "available_quantity": min(
                            product.available_quantity,
                            stored_size.stock_quantity - stored_size.reserved,
                        )
                        if product and stored_size
                        else 0,
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
                    "product_size_id": i.product_size_id,
                    "size": i.size_snapshot,
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
            seen: set[int] = set()
            for line in sorted(
                payload["items"], key=lambda x: (x["product_id"], x.get("product_size_id") or 0)
            ):
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
                size = await self._size(s, line["product_id"], line.get("product_size_id"))
                if size.id in seen:
                    raise BusinessError(422, "Sản phẩm và size bị trùng.")
                seen.add(size.id)
                product = await SqlCatalogRepository(s, self.profile).get_product(
                    line["product_id"]
                )
                if (
                    not offer
                    or not stock
                    or not product
                    or product.price_vnd != line["expected_price_vnd"]
                    or min(stock.on_hand - stock.reserved, size.stock_quantity - size.reserved)
                    < line["quantity"]
                ):
                    raise BusinessError(
                        409, "Giá hoặc tồn kho đã thay đổi. Hãy kiểm tra lại giỏ hàng."
                    )
                stock.reserved += line["quantity"]
                stock.version += 1
                stock.updated_at = datetime.now(UTC)
                size.reserved += line["quantity"]
                selected.append((line, offer, stock, product, size))
            row = Order(
                id=uid(),
                code="HM" + uuid.uuid4().hex[:14].upper(),
                user_id=actor.id,
                status="CONFIRMED",
                total_vnd=sum(
                    line["quantity"] * product.price_vnd
                    for line, offer, stock, product, size in selected
                ),
                data_profile=self.profile,
                address=payload["address"],
                idempotency_key=key,
                request_hash=hashed,
            )
            s.add(row)
            await s.flush()
            for line, offer, _stock, product, size in selected:
                s.add(
                    OrderItem(
                        id=uid(),
                        order_id=row.id,
                        product_id=product.id,
                        product_size_id=size.id,
                        size_snapshot=size.size,
                        name_snapshot=product.name_vi,
                        unit_price_vnd=product.price_vnd,
                        quantity=line["quantity"],
                    )
                )
                s.add(
                    StockReservation(
                        order_id=row.id,
                        offer_id=offer.id,
                        product_size_id=size.id,
                        quantity=line["quantity"],
                        status="held",
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
                    .order_by(StockReservation.offer_id, StockReservation.product_size_id)
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
                size = await s.scalar(
                    select(ProductSize)
                    .where(ProductSize.id == reserve.product_size_id)
                    .with_for_update()
                )
                if size is None:
                    raise BusinessError(409, "Không thể cập nhật tồn kho theo size.")
                size.reserved -= reserve.quantity
                if status == "SHIPPED":
                    size.stock_quantity -= reserve.quantity
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
            query_ids = [r.id for r in rows]
            filters = (
                await s.scalars(
                    select(SearchFilterRow)
                    .where(SearchFilterRow.query_id.in_(query_ids))
                    .order_by(SearchFilterRow.kind, SearchFilterRow.position)
                )
            ).all()
            results = (
                await s.scalars(
                    select(SearchResultRow)
                    .where(SearchResultRow.query_id.in_(query_ids))
                    .order_by(SearchResultRow.rank)
                )
            ).all()
            return [
                {
                    "id": r.id,
                    "text": r.raw_text,
                    "modality": r.modality,
                    "normalized_text": r.normalized_text,
                    "encoder_version": r.encoder_version,
                    "filters": [
                        {
                            "kind": f.kind,
                            "key": f.key,
                            "value": f.value,
                            "origin": f.origin,
                            "operator": f.operator,
                            "confidence": f.confidence,
                            "position": f.position,
                        }
                        for f in filters
                        if f.query_id == r.id
                    ],
                    "results": [
                        {
                            "product_id": item.product_id,
                            "rank": item.rank,
                            "score": item.final_score,
                            "relevance_score": item.relevance_score,
                            "preference_score": item.preference_score,
                            "explanation": item.explanation,
                        }
                        for item in results
                        if item.query_id == r.id
                    ],
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]

    async def remember(self, actor: Actor, record: SearchRecord) -> None:
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
            rep = record.query
            query = SearchQuery(
                id=uid(),
                user_id=actor.id,
                raw_text=rep.raw_text[:300],
                modality=rep.modality,
                normalized_text=rep.normalized_text[:300],
                encoder_version=rep.image_vector_ref,
            )
            s.add(query)
            await s.flush()
            for kind, constraints in (
                ("hard", rep.hard_filters),
                ("soft", rep.soft_preferences),
                ("relaxed", rep.relaxed_filters),
            ):
                for position, constraint in enumerate(constraints):
                    s.add(
                        SearchFilterRow(
                            id=uid(),
                            query_id=query.id,
                            kind=kind,
                            position=position,
                            key=constraint.key,
                            value=constraint.value,
                            origin=constraint.origin,
                            operator=constraint.operator,
                            confidence=constraint.confidence,
                        )
                    )
            for item in record.items[:24]:
                s.add(
                    SearchResultRow(
                        query_id=query.id,
                        product_id=item.product_id,
                        rank=item.rank,
                        final_score=item.score,
                        explanation=item.explanation,
                        relevance_score=item.relevance_score,
                        preference_score=item.preference_score,
                    )
                )

    async def manage(self, actor: Actor, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not {"admin", "seller"}.intersection(actor.roles):
            raise BusinessError(403, "Bạn không có quyền quản lý sản phẩm.")
        admin = "admin" in actor.roles
        if self.profile == "real_demo" and not admin and action not in {"list", "images"}:
            raise BusinessError(
                409,
                "Danh mục ảnh thật được nhập có kiểm duyệt; biểu mẫu chỉnh sửa chưa được hỗ trợ.",
            )
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
                    category = await s.get(CategoryRow, record["category_id"])
                    if not category or not category.is_active:
                        errors.append(
                            {
                                "row": index,
                                "field": "category_id",
                                "message": "Danh mục không tồn tại hoặc đã ngừng sử dụng.",
                            }
                        )
                    try:
                        if record.get("image_url") or record.get("image_urls"):
                            for url in record.get("image_urls") or [record["image_url"]]:
                                validate_image_url(url)
                            if not record.get("image_rights_confirmed"):
                                raise ValueError("Cần xác nhận quyền sử dụng ảnh.")
                        else:
                            await self._approved_image(s, record["image_id"])
                    except (ValueError, BusinessError):
                        errors.append(
                            {
                                "row": index,
                                "field": "image_url",
                                "message": "Ảnh hoặc quyền sử dụng chưa hợp lệ.",
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
                ids = [p.id for p, _ in rows]
                variants = {
                    v.product_id: v
                    for v in (
                        await s.scalars(
                            select(ProductVariant).where(ProductVariant.product_id.in_(ids))
                        )
                    ).all()
                }
                all_photos = (
                    await s.scalars(
                        select(ProductImage)
                        .where(ProductImage.product_id.in_(ids))
                        .order_by(
                            ProductImage.is_primary.desc(), ProductImage.sort_order, ProductImage.id
                        )
                    )
                ).all()
                photos = {image.product_id: image for image in all_photos if image.is_primary}
                materials = {
                    m.product_id: m.display_value_vi
                    for m in (
                        await s.scalars(
                            select(ProductAttribute).where(
                                ProductAttribute.product_id.in_(ids),
                                ProductAttribute.attribute_key == "material",
                            )
                        )
                    ).all()
                }
                sizes = (
                    await s.scalars(
                        select(ProductSize)
                        .where(ProductSize.product_id.in_(ids))
                        .order_by(ProductSize.id)
                    )
                ).all()
                return {
                    "items": [
                        {
                            "id": p.id,
                            "name": p.name_vi,
                            "description": p.description_vi,
                            "brand": p.brand_id or "",
                            "color": variants[p.id].color,
                            "material": materials.get(p.id, ""),
                            "image_id": photos[p.id].id if p.id in photos else "",
                            "image_url": photos[p.id].storage_key if p.id in photos else "",
                            "image_urls": [
                                image.storage_key
                                for image in all_photos
                                if image.product_id == p.id
                            ],
                            "sizes": [
                                {
                                    "size": size.size,
                                    "stock": size.stock_quantity,
                                    "reserved": size.reserved,
                                }
                                for size in sizes
                                if size.product_id == p.id
                            ],
                            "updated_at": p.updated_at.isoformat(),
                            "category_id": p.category_id,
                            "status": p.publication_status,
                            "review": p.verification_status,
                            "price_vnd": o.price_vnd,
                            "seller_id": o.seller_id,
                        }
                        for p, o in rows
                    ],
                    "read_only": self.profile == "real_demo" and not admin,
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
            if (
                not product
                or product.data_profile != self.profile
                or not offer
                or (not admin and offer.seller_id != actor.id)
            ):
                raise BusinessError(404, "Không tìm thấy sản phẩm quản lý.")
            if action == "publish":
                if not admin:
                    raise BusinessError(403, "Chỉ quản trị viên được duyệt xuất bản.")
                category = await s.get(CategoryRow, product.category_id)
                if not category or not category.is_active:
                    raise BusinessError(409, "Hãy chọn danh mục đang sử dụng trước khi xuất bản.")
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
                sizes = (
                    await s.scalars(
                        select(ProductSize)
                        .where(ProductSize.product_id == product.id)
                        .order_by(ProductSize.id)
                        .with_for_update()
                    )
                ).all()
                metadata_fields = {
                    "name",
                    "description",
                    "category_id",
                    "image_id",
                    "image_url",
                    "image_urls",
                    "image_rights_confirmed",
                    "color",
                    "material",
                    "brand",
                    "sizes",
                }
                if not admin and metadata_fields.intersection(payload):
                    raise BusinessError(
                        403, "Chỉ quản trị viên được sửa thông tin và size sản phẩm."
                    )
                requested_sizes = payload.get("sizes")
                if requested_sizes is not None:
                    requested = {row["size"]: row["stock"] for row in requested_sizes}
                    for size in sizes:
                        quantity = requested.pop(size.size, 0)
                        if quantity < size.reserved:
                            raise BusinessError(
                                409, f"Tồn kho size {size.size} không được thấp hơn số đang giữ."
                            )
                        size.stock_quantity = quantity
                    for size_name, quantity in requested.items():
                        s.add(
                            ProductSize(
                                product_id=product.id,
                                size=size_name,
                                stock_quantity=quantity,
                                reserved=0,
                            )
                        )
                    variant = await s.scalar(
                        select(ProductVariant).where(ProductVariant.product_id == product.id)
                    )
                    if variant:
                        variant.size = ", ".join(row["size"] for row in requested_sizes)
                        variant.option_values = {
                            **variant.option_values,
                            "available_sizes": [row["size"] for row in requested_sizes],
                        }
                elif len(sizes) == 1:
                    sizes[0].stock_quantity = payload["stock"]
                else:
                    raise BusinessError(409, "Hãy nhập tồn kho của từng size.")
                if admin:
                    await self._edit_details(s, actor, product, payload)
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
                        SourceProduct.source_id
                        == ("operator-" if self.profile == "demo_seed" else "operator-public-")
                        + offer.seller_id,
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
        if self.profile not in {"demo_seed", "real_demo"} or not p.get("original_data_confirmed"):
            raise BusinessError(
                422, "Chỉ tạo dữ liệu mô phỏng do bạn có quyền sử dụng trong chế độ này."
            )
        category = await s.get(CategoryRow, p["category_id"])
        if not category or not category.is_active:
            raise BusinessError(422, "Danh mục không tồn tại hoặc đã ngừng sử dụng.")
        image = await self._approved_image(s, p["image_id"]) if p.get("image_id") else None
        urls = p.get("image_urls") or ([p["image_url"]] if p.get("image_url") else [])
        cover_url = urls[0] if urls else ""
        photo = (
            await self._inspect_external(cover_url, p.get("image_rights_confirmed", False))
            if urls
            else {}
        )
        if image is None and not photo:
            raise BusinessError(422, "Hãy nhập URL ảnh sản phẩm.")
        pid = ("demo-" if self.profile == "demo_seed" else "hoodoo-") + uid()
        source = ("operator-" if self.profile == "demo_seed" else "operator-public-") + actor.id
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
                rights_status="demo" if self.profile == "demo_seed" else "approved",
                allowed_use=(
                    "Original product metadata explicitly affirmed CC0 by operator; "
                    "image sources retained separately"
                ),
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
                brand_id=p.get("brand") or None,
                gender="nam",
                publication_status="draft",
                verification_status="pending",
                data_profile=self.profile,
                search_text_normalized=normalize(p["name"] + " " + p["description"]),
            )
        )
        await s.flush()
        s.add(
            ProductSource(
                product_id=pid,
                source_id=source,
                external_id=pid,
                field_provenance={"metadata": "operator-original", "image": "separately-reviewed"},
            )
        )
        s.add(
            ProductImage(
                id="image-" + pid,
                product_id=pid,
                storage_key=image.storage_key if image else cover_url,
                sha256=image.sha256 if image else photo["sha256"],
                width=image.width if image else photo["width"],
                height=image.height if image else photo["height"],
                license_status="demo" if self.profile == "demo_seed" else "approved",
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
                size=", ".join(row["size"] for row in p["sizes"]) if p.get("sizes") else p["size"],
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
        if p.get("sizes"):
            await s.flush()
            for row in p["sizes"]:
                s.add(
                    ProductSize(
                        product_id=pid, size=row["size"], stock_quantity=row["stock"], reserved=0
                    )
                )
        else:
            await initialize_sizes(s, pid)
        if image:
            await self._retain_image_sources(s, pid, image)
        else:
            await self._record_external_source(s, actor, pid, cover_url, photo)
            await self._set_gallery(s, actor, pid, urls, p.get("image_rights_confirmed", False))
        return {"id": pid, "batch_id": batch, "status": "draft", "review": "pending"}

    async def _approved_image(self, s: AsyncSession, image_id: str) -> ProductImage:
        image = await s.get(ProductImage, image_id)
        owner = await s.get(ProductRow, image.product_id) if image else None
        allowed = "demo" if self.profile == "demo_seed" else "approved"
        rights = (
            (
                await s.scalars(
                    select(DataSource.rights_status)
                    .join(ProductSource, ProductSource.source_id == DataSource.id)
                    .where(ProductSource.product_id == owner.id)
                )
            ).all()
            if owner
            else []
        )
        if (
            not image
            or not owner
            or owner.data_profile != self.profile
            or image.license_status != allowed
            or not rights
            or any(right != allowed for right in rights)
        ):
            raise BusinessError(422, "Hãy chọn ảnh trong thư viện đã duyệt quyền sử dụng.")
        return image

    async def _retain_image_sources(self, s: AsyncSession, pid: str, image: ProductImage) -> None:
        sources = (
            await s.scalars(
                select(ProductSource).where(ProductSource.product_id == image.product_id)
            )
        ).all()
        for source in sources:
            current = await s.get(ProductSource, (pid, source.source_id))
            evidence = {
                "image": {
                    "image_id": image.id,
                    "source_product_id": image.product_id,
                    "external_id": source.external_id,
                }
            }
            if current:
                current.field_provenance = {**current.field_provenance, **evidence}
            else:
                s.add(
                    ProductSource(
                        product_id=pid,
                        source_id=source.source_id,
                        external_id=source.external_id,
                        field_provenance=evidence,
                    )
                )
        await s.flush()

    async def _edit_details(
        self, s: AsyncSession, actor: Actor, product: ProductRow, payload: dict[str, Any]
    ) -> None:
        if payload.get("category_id") is not None:
            category = await s.get(CategoryRow, payload["category_id"])
            if not category or not category.is_active:
                raise BusinessError(422, "Danh mục không tồn tại hoặc đã ngừng sử dụng.")
            product.category_id = category.id
        if payload.get("name") is not None:
            product.name_vi = payload["name"]
        if payload.get("description") is not None:
            product.description_vi = payload["description"]
        if "brand" in payload:
            product.brand_id = payload["brand"] or None
        product.search_text_normalized = normalize(product.name_vi + " " + product.description_vi)
        variant = await s.scalar(
            select(ProductVariant).where(ProductVariant.product_id == product.id)
        )
        if variant and payload.get("color") is not None:
            variant.color = payload["color"]
        if payload.get("material") is not None:
            material = await s.get(ProductAttribute, (product.id, "material"))
            if material:
                material.display_value_vi = payload["material"]
                material.canonical_value = normalize(payload["material"])
                material.review_status = "verified"
                material.provenance = "admin:" + actor.id
            else:
                s.add(
                    ProductAttribute(
                        product_id=product.id,
                        attribute_key="material",
                        canonical_value=normalize(payload["material"]),
                        display_value_vi=payload["material"],
                        confidence=100,
                        review_status="verified",
                        provenance="admin:" + actor.id,
                    )
                )
        urls = payload.get("image_urls") or (
            [payload["image_url"]] if payload.get("image_url") else None
        )
        if urls is not None:
            await self._set_gallery(
                s, actor, product.id, urls, payload.get("image_rights_confirmed", False)
            )
        if payload.get("image_id") is not None:
            image = await self._approved_image(s, payload["image_id"])
            primary = await s.scalar(
                select(ProductImage).where(
                    ProductImage.product_id == product.id, ProductImage.is_primary.is_(True)
                )
            )
            if primary and primary.id != image.id:
                await self._retain_image_sources(s, product.id, image)
                await s.execute(delete(ImageEmbedding).where(ImageEmbedding.image_id == primary.id))
                for field in ("storage_key", "sha256", "width", "height", "license_status"):
                    setattr(primary, field, getattr(image, field))
                primary.alt_vi = product.name_vi
        sources = (
            await s.scalars(select(ProductSource).where(ProductSource.product_id == product.id))
        ).all()
        for source in sources:
            source.field_provenance = {
                **source.field_provenance,
                "admin_edit": {
                    "actor_id": actor.id,
                    "at": datetime.now(UTC).isoformat(),
                    "fields": sorted(payload.keys() - {"id"}),
                },
            }

    async def _inspect_external(self, url: str, confirmed: bool) -> dict[str, Any]:
        if not confirmed:
            raise BusinessError(422, "Cần xác nhận quyền sử dụng ảnh khi thêm hoặc đổi URL.")
        try:
            validate_image_url(url)
        except ValueError as error:
            raise BusinessError(422, str(error)) from error
        try:
            return await inspect_image(url)
        except (httpx.HTTPError, ValueError, OSError, Image.DecompressionBombError) as error:
            raise BusinessError(
                422,
                "Không đọc được ảnh. Hãy dùng URL ảnh trực tiếp JPEG, PNG hoặc WebP, tối đa 5 MB.",
            ) from error

    async def _record_external_source(
        self, s: AsyncSession, actor: Actor, pid: str, url: str, photo: dict[str, Any]
    ) -> None:
        allowed = "demo" if self.profile == "demo_seed" else "approved"
        source_id = "url-image-" + self.profile + "-" + photo["sha256"][:32]
        source = await s.get(DataSource, source_id)
        if source and source.rights_status != allowed:
            raise BusinessError(422, "Nguồn ảnh đã bị thu hồi quyền sử dụng.")
        now = datetime.now(UTC)
        await s.execute(
            insert(DataSource)
            .values(
                id=source_id,
                name="Ảnh URL do admin xác nhận quyền",
                version="1",
                license="Operator-confirmed local demo reuse",
                rights_status=allowed,
                allowed_use="Operator explicitly confirmed permission for local storefront display",
                last_checked_at=now,
            )
            .on_conflict_do_nothing()
        )
        raw = await s.get(SourceProduct, (source_id, photo["sha256"]))
        if raw is None:
            batch_id = uid()
            data = {"url": url, **photo, "rights_confirmed_by": actor.id}
            s.add(
                ImportBatch(
                    id=batch_id,
                    source_id=source_id,
                    started_at=now,
                    status="approved",
                    counts={"images": 1},
                    errors=[],
                )
            )
            await s.flush()
            s.add(
                SourceProduct(
                    source_id=source_id,
                    external_id=photo["sha256"],
                    raw_json=data,
                    raw_hash=hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(),
                    imported_at=now,
                    batch_id=batch_id,
                )
            )
            await s.flush()
        link = await s.get(ProductSource, (pid, source_id))
        if link is None:
            s.add(
                ProductSource(
                    product_id=pid,
                    source_id=source_id,
                    external_id=photo["sha256"],
                    field_provenance={"image_url": url, "rights_confirmed_by": actor.id},
                )
            )
        await s.flush()

    async def _set_gallery(
        self, s: AsyncSession, actor: Actor, pid: str, urls: list[str], confirmed: bool
    ) -> None:
        existing = (
            await s.scalars(
                select(ProductImage).where(ProductImage.product_id == pid).with_for_update()
            )
        ).all()
        by_url = {image.storage_key: image for image in existing}
        gate = asyncio.Semaphore(3)

        async def inspect(url: str) -> tuple[str, dict[str, Any]]:
            async with gate:
                return url, await self._inspect_external(url, confirmed)

        metadata = dict(await asyncio.gather(*(inspect(url) for url in urls if url not in by_url)))
        # Clear the partial unique primary-image constraint before reordering.
        for image in existing:
            image.is_primary = False
        await s.flush()
        for image in existing:
            if image.storage_key not in urls:
                await s.execute(delete(ImageEmbedding).where(ImageEmbedding.image_id == image.id))
                await s.delete(image)
        await s.flush()
        product = await s.get(ProductRow, pid)
        for index, url in enumerate(urls):
            selected_image = by_url.get(url)
            if selected_image is None:
                photo = metadata[url]
                await self._record_external_source(s, actor, pid, url, photo)
                selected_image = ProductImage(
                    id="image-" + uid(),
                    product_id=pid,
                    storage_key=url,
                    **photo,
                    license_status="demo" if self.profile == "demo_seed" else "approved",
                    is_primary=False,
                    alt_vi=product.name_vi if product else "Ảnh sản phẩm",
                    sort_order=index,
                )
                s.add(selected_image)
            selected_image.is_primary = index == 0
            selected_image.sort_order = index
        await s.flush()
