"""P2 contracts only. No live provider configured or implemented."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class PaymentReceipt:
    external_reference: str
    amount_vnd: int
    status: Literal["authorized", "captured", "refunded", "failed"]


class PaymentGateway(Protocol):
    async def authorize(
        self, order_id: str, amount_vnd: int, idempotency_key: str
    ) -> PaymentReceipt: ...
    async def refund(
        self, reference: str, amount_vnd: int, idempotency_key: str
    ) -> PaymentReceipt: ...


@dataclass(frozen=True)
class TrackingEvent:
    reference: str
    status: str
    occurred_at: str


class ShippingProvider(Protocol):
    async def create_shipment(
        self, order_id: str, address_reference: str, idempotency_key: str
    ) -> str: ...
    async def tracking(self, reference: str) -> tuple[TrackingEvent, ...]: ...


class FinanceReconciliation(Protocol):
    async def reconcile(self, settlement_reference: str) -> str: ...


class EscrowDisputes(Protocol):
    async def open_dispute(self, order_id: str, actor_id: str, reason: str) -> str: ...
