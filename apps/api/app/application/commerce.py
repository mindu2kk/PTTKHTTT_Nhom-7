import hashlib
import re
import secrets
from typing import Any

from app.domain.commerce import Actor, BusinessError, CommerceStore, Passwords


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
