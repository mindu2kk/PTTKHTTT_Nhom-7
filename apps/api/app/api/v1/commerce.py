import secrets
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.application.commerce import CommerceService
from app.core.config import get_settings
from app.core.dependencies import commerce_service
from app.domain.commerce import Actor, BusinessError

router = APIRouter(prefix="/api/v1", tags=["Tài khoản và thương mại mô phỏng"])
Service = Annotated[CommerceService, Depends(commerce_service)]


async def optional_actor(request: Request, service: Service) -> Actor | None:
    return await service.identify(request.cookies.get("hm_session"))


async def require_actor(actor: Annotated[Actor | None, Depends(optional_actor)]) -> Actor:
    if not actor:
        raise BusinessError(401, "Đăng nhập để tra cứu đơn hàng của bạn.")
    return actor


Owner = Annotated[Actor, Depends(require_actor)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(StrictModel):
    email: str = Field(min_length=5, max_length=250)
    password: str = Field(min_length=10, max_length=128)


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    roles: tuple[str, ...]
    history_opt_in: bool


def csrf_cookie(response: Response) -> str:
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        "hm_csrf",
        token,
        httponly=False,
        secure=get_settings().cookie_secure,
        samesite="strict",
        max_age=7 * 86400,
        path="/",
    )
    return token


@router.get("/auth/csrf")
async def csrf(response: Response) -> dict[str, str]:
    return {"token": csrf_cookie(response)}


async def sign_in(
    body: Credentials,
    service: CommerceService,
    response: Response,
    register: bool,
    request: Request,
) -> AccountResponse:
    actor, token = await service.authenticate(body.email, body.password, register)
    await service.logout(request.cookies.get("hm_session"))
    response.set_cookie(
        "hm_session",
        token,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        max_age=7 * 86400,
        path="/",
    )
    csrf_cookie(response)
    return AccountResponse.model_validate(actor)


@router.post("/auth/register", response_model=AccountResponse, status_code=201)
async def register(
    body: Credentials, service: Service, response: Response, request: Request
) -> AccountResponse:
    return await sign_in(body, service, response, True, request)


@router.post("/auth/login", response_model=AccountResponse)
async def login(
    body: Credentials, service: Service, response: Response, request: Request
) -> AccountResponse:
    return await sign_in(body, service, response, False, request)


@router.post("/auth/logout")
async def logout(request: Request, response: Response, service: Service) -> dict[str, bool]:
    await service.logout(request.cookies.get("hm_session"))
    response.delete_cookie("hm_session", path="/")
    response.delete_cookie("hm_csrf", path="/")
    return {"ok": True}


@router.get("/auth/me", response_model=AccountResponse)
async def me(actor: Owner) -> AccountResponse:
    return AccountResponse.model_validate(actor)


class CartLine(StrictModel):
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=99)


class CartBody(StrictModel):
    items: list[CartLine] = Field(max_length=50)

    @model_validator(mode="after")
    def unique(self) -> "CartBody":
        if len({x.product_id for x in self.items}) != len(self.items):
            raise ValueError("duplicate product")
        return self


@router.get("/cart")
async def cart_get(actor: Owner, service: Service) -> dict[str, Any]:
    return await service.store.cart(actor, None)


@router.put("/cart")
async def cart_put(body: CartBody, actor: Owner, service: Service) -> dict[str, Any]:
    return await service.store.cart(actor, [x.model_dump() for x in body.items])


class CheckoutLine(CartLine):
    expected_price_vnd: int = Field(gt=0, le=10**12)


class Address(StrictModel):
    recipient: str = Field(min_length=2, max_length=100)
    phone: str = Field(pattern=r"^\+?[0-9 ]{9,15}$")
    address_line: str = Field(min_length=8, max_length=300)


class CheckoutBody(StrictModel):
    items: list[CheckoutLine] = Field(min_length=1, max_length=50)
    address: Address
    method: Literal["cod", "mock"] = "cod"

    @model_validator(mode="after")
    def unique(self) -> "CheckoutBody":
        if len({x.product_id for x in self.items}) != len(self.items):
            raise ValueError("duplicate product")
        return self


class OrderLineResponse(BaseModel):
    product_id: str
    name: str
    unit_price_vnd: int
    quantity: int


class OrderResponse(BaseModel):
    code: str
    status: str
    total_vnd: int
    created_at: str
    data_profile: str
    address: dict[str, str]
    payment_method: str
    payment_status: str
    shipment_status: str
    items: list[OrderLineResponse]


@router.post("/checkout", response_model=OrderResponse, status_code=201)
async def checkout(
    body: CheckoutBody,
    actor: Owner,
    service: Service,
    idempotency_key: Annotated[
        str, Header(min_length=16, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    ],
) -> dict[str, Any]:
    return await service.store.checkout(actor, idempotency_key, body.model_dump())


@router.get("/orders", response_model=list[OrderResponse])
async def orders(actor: Owner, service: Service) -> list[dict[str, Any]]:
    return await service.store.orders(actor)


@router.get("/orders/{code}", response_model=OrderResponse)
async def order(code: str, actor: Owner, service: Service) -> dict[str, Any]:
    return await service.order(actor, code)


class StatusBody(StrictModel):
    status: Literal["CANCELLED", "PACKING", "SHIPPED", "DELIVERED"]


@router.patch("/orders/{code}", response_model=OrderResponse)
async def transition(code: str, body: StatusBody, actor: Owner, service: Service) -> dict[str, Any]:
    return await service.store.transition(actor, code, body.status)


class HistoryBody(StrictModel):
    enabled: bool


@router.get("/history")
async def history(actor: Owner, service: Service) -> list[dict[str, Any]]:
    return await service.store.history(actor, "list")


@router.patch("/history")
async def history_setting(body: HistoryBody, actor: Owner, service: Service) -> dict[str, bool]:
    await service.store.history(actor, "enable" if body.enabled else "disable")
    return {"enabled": body.enabled}


@router.delete("/history")
async def history_delete(actor: Owner, service: Service) -> dict[str, bool]:
    await service.store.history(actor, "delete")
    return {"ok": True}


class DraftBody(StrictModel):
    name: str = Field(min_length=3, max_length=250)
    description: str = Field(min_length=10, max_length=3000)
    category_id: str = Field(min_length=1, max_length=80)
    image_id: str = Field(min_length=1, max_length=100)
    price_vnd: int = Field(gt=0, le=10**12)
    stock: int = Field(ge=0, le=1000000)
    color: str = Field(min_length=1, max_length=40)
    material: str = Field(min_length=1, max_length=100)
    size: str = Field(min_length=1, max_length=30)
    original_data_confirmed: Literal[True]


class OfferBody(StrictModel):
    price_vnd: int = Field(gt=0, le=10**12)
    stock: int = Field(ge=0, le=1000000)


class ImportBody(StrictModel):
    records: list[DraftBody] = Field(min_length=1, max_length=20)


@router.post("/manage/imports/preview")
async def preview_import(body: ImportBody, actor: Owner, service: Service) -> dict[str, Any]:
    return await service.store.manage(actor, "preview_import", body.model_dump())


@router.post("/manage/imports", status_code=201)
async def commit_import(body: ImportBody, actor: Owner, service: Service) -> dict[str, Any]:
    return await service.store.manage(actor, "import", body.model_dump())


@router.get("/manage/products")
async def managed(actor: Owner, service: Service) -> dict[str, Any]:
    return await service.store.manage(actor, "list", {})


@router.get("/manage/images")
async def managed_images(actor: Owner, service: Service) -> dict[str, Any]:
    return await service.store.manage(actor, "images", {})


@router.post("/manage/products", status_code=201)
async def create_draft(body: DraftBody, actor: Owner, service: Service) -> dict[str, Any]:
    return await service.store.manage(actor, "create", body.model_dump())


@router.patch("/manage/products/{pid}")
async def update_offer(pid: str, body: OfferBody, actor: Owner, service: Service) -> dict[str, Any]:
    return await service.store.manage(actor, "update", {"id": pid, **body.model_dump()})


@router.post("/manage/products/{pid}/{action}")
async def review(
    pid: str, action: Literal["publish", "archive"], actor: Owner, service: Service
) -> dict[str, Any]:
    return await service.store.manage(actor, action, {"id": pid})
