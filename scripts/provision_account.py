"""Explicit local operator command. Password via hidden prompt, never stdout/argv."""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.core.dependencies import commerce_service
from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import Order, SellerProfile, User, UserRole


async def run(args):
    try:
        password = getpass.getpass("Mật khẩu mới (10-128 ký tự, không hiển thị): ")
        if not 10 <= len(password) <= 128:
            raise ValueError("Mật khẩu cần 10-128 ký tự.")
        service = commerce_service()
        existing = await service.store.credentials(args.email.strip().lower())
        if existing:
            actor = existing[0]
            async with session_factory.begin() as s:
                await s.execute(
                    update(User)
                    .where(User.id == actor.id)
                    .values(password_hash=await service.passwords.hash(password))
                )
        else:
            actor, _ = await service.authenticate(args.email, password, True)
        async with session_factory.begin() as s:
            await s.execute(
                insert(UserRole)
                .values(user_id=actor.id, role=args.role)
                .on_conflict_do_nothing()
            )
            if args.role == "seller":
                await s.execute(
                    insert(SellerProfile)
                    .values(user_id=actor.id, name="Người bán mô phỏng", approved=True)
                    .on_conflict_do_update(
                        index_elements=[SellerProfile.user_id], set_={"approved": True}
                    )
                )
            if args.bind_fixture_order:
                order = await s.scalar(
                    select(Order).where(Order.id == "fixture-order").with_for_update()
                )
                if not order or order.user_id not in {"fixture-customer", actor.id}:
                    raise RuntimeError("Đơn mẫu đã có chủ khác; không ghi đè.")
                order.user_id = actor.id
        print("Đã cấp quyền tài khoản cục bộ. Mật khẩu không được ghi log.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--role", choices=["customer", "seller", "admin"], default="customer"
    )
    parser.add_argument(
        "--bind-fixture-order",
        action="store_true",
        help="Gán rõ ràng đơn mô phỏng 20261005, chỉ khi chưa có chủ.",
    )
    asyncio.run(run(parser.parse_args()))
