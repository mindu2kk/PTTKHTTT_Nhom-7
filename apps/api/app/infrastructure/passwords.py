import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


class ArgonPasswords:
    def __init__(self) -> None:
        self.hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
        self.dummy = self.hasher.hash("unusable-random-dummy-password")
        self.gate = asyncio.Semaphore(2)

    async def hash(self, password: str) -> str:
        async with self.gate:
            return await asyncio.to_thread(self.hasher.hash, password)

    async def verify(self, digest: str | None, password: str) -> bool:
        async with self.gate:
            try:
                valid = await asyncio.to_thread(self.hasher.verify, digest or self.dummy, password)
                return valid and digest is not None
            except (VerificationError, InvalidHashError):
                return False
