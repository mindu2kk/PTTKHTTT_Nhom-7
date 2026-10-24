"""Temporary local E2E setup/restore of the isolated course order, with owner guards."""

import asyncio
import sys

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import Order, User, UserRole


async def run(user_id: str, action: str) -> None:
    try:
        async with session_factory.begin() as s:
            user = await s.get(User, user_id)
            if (
                not user
                or not user.email.startswith("browser-")
                or not user.email.endswith("@example.invalid")
            ):
                raise RuntimeError(
                    "Only this harness's freshly generated browser account may own the test fixture."
                )
            if action == "grant-admin":
                await s.execute(
                    insert(UserRole)
                    .values(user_id=user_id, role="admin")
                    .on_conflict_do_nothing()
                )
                return
            if action == "revoke-admin":
                await s.execute(
                    delete(UserRole).where(
                        UserRole.user_id == user_id, UserRole.role == "admin"
                    )
                )
                return
            order = await s.scalar(
                select(Order).where(Order.id == "fixture-order").with_for_update()
            )
            expected = "fixture-customer" if action == "bind" else user_id
            target = user_id if action == "bind" else "fixture-customer"
            if not order or order.user_id not in {expected, target}:
                raise RuntimeError("Fixture has another owner; preserved.")
            order.user_id = target
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1], sys.argv[2]))
