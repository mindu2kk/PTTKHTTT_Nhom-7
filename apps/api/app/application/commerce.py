import hashlib
import re
import secrets
from typing import Any

from app.domain.commerce import Actor, BusinessError, CommerceStore, Passwords
from app.domain.search import SearchRecord


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class CommerceService:
    def __init__(self, store: CommerceStore, passwords: Passwords):
        self.store, self.passwords = store, passwords

    async def identify(self, token: str | None) -> Actor | None:
        return await self.store.session(digest(token)) if token else None

    async def authenticate(self, email: str, password: str, register: bool) -> tuple[Actor, str]:
        email = email.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or not 10 <= len(password) <= 128:
            raise BusinessError(422, "Email hoặc mật khẩu không hợp lệ. Mật khẩu cần 10–128 ký tự.")
        if register:
            actor = await self.store.register(email, await self.passwords.hash(password))
        else:
            found = await self.store.credentials(email)
            verified = await self.passwords.verify(found[1] if found else None, password)
            if not found or not verified:
                raise BusinessError(401, "Email hoặc mật khẩu không đúng.")
            actor = found[0]
        token = secrets.token_urlsafe(32)
        await self.store.start_session(actor.id, digest(token))
        return actor, token

    async def logout(self, token: str | None) -> None:
        if token:
            await self.store.end_session(digest(token))

    async def order(self, actor: Actor, code: str) -> dict[str, Any]:
        rows = await self.store.orders(actor, code)
        if not rows:
            raise BusinessError(404, "Không tìm thấy đơn hàng của bạn.")
        return rows[0]

    async def cart(self, actor: Actor, lines: list[dict[str, Any]] | None) -> dict[str, Any]:
        return await self.store.cart(actor, lines)

    async def checkout(self, actor: Actor, key: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.store.checkout(actor, key, payload)

    async def orders(self, actor: Actor) -> list[dict[str, Any]]:
        return await self.store.orders(actor)

    async def transition(self, actor: Actor, code: str, status: str) -> dict[str, Any]:
        if status not in {"CANCELLED", "PACKING", "SHIPPED", "DELIVERED"}:
            raise BusinessError(422, "Trạng thái đơn hàng không hợp lệ.")
        if status != "CANCELLED" and "admin" not in actor.roles:
            raise BusinessError(403, "Bạn không có quyền cập nhật trạng thái này.")
        return await self.store.transition(actor, code, status)

    async def history(self, actor: Actor, action: str) -> list[dict[str, Any]]:
        if action not in {"list", "enable", "disable", "delete"}:
            raise BusinessError(422, "Thao tác lịch sử không hợp lệ.")
        return await self.store.history(actor, action)

    async def remember(self, actor: Actor, record: SearchRecord) -> None:
        await self.store.remember(actor, record)

    async def manage(self, actor: Actor, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not {"admin", "seller"}.intersection(actor.roles):
            raise BusinessError(403, "Bạn không có quyền quản lý sản phẩm.")
        return await self.store.manage(actor, action, payload)
