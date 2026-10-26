from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.commerce import optional_actor
from app.api.v1.search import SearchResponse, remember_safely
from app.application.commerce import CommerceService
from app.application.image_search import ImageSearchService
from app.application.speech import SpeechService
from app.core.dependencies import commerce_service, image_service, speech_service
from app.domain.commerce import Actor
from app.domain.media import MediaError
from app.domain.search import SearchOptions

router = APIRouter(prefix="/api/v1/search", tags=["Đa phương thức"])


@router.post("/image", response_model=SearchResponse)
async def search_image(
    service: Annotated[ImageSearchService, Depends(image_service)],
    actor: Annotated[Actor | None, Depends(optional_actor)],
    commerce: Annotated[CommerceService, Depends(commerce_service)],
    tasks: BackgroundTasks,
    image: Annotated[UploadFile, File()],
    text: Annotated[str, Form(max_length=300)] = "",
    category: Annotated[str | None, Form(max_length=100)] = None,
    price_min: Annotated[int | None, Form(ge=0, le=10**12)] = None,
    price_max: Annotated[int | None, Form(ge=0, le=10**12)] = None,
    color: Annotated[str | None, Form(max_length=40)] = None,
    page: Annotated[int, Form(ge=1, le=1000)] = 1,
    page_size: Annotated[int, Form(ge=1, le=24)] = 12,
    top_k: Annotated[int | None, Form(ge=1, le=100)] = None,
) -> SearchResponse:
    try:
        if price_min is not None and price_max is not None and price_min > price_max:
            raise HTTPException(422, "Khoảng giá không hợp lệ.")
        raw = await image.read(5 * 1024 * 1024 + 1)
        result = await service.find(
            raw,
            image.content_type or "",
            image.filename or "",
            text,
            SearchOptions(
                category=category,
                price_min=price_min,
                price_max=price_max,
                color=color,
                page=page,
                page_size=page_size,
                top_k=top_k,
            ),
        )
        response = SearchResponse.model_validate(result)
        if actor:
            tasks.add_task(remember_safely, commerce, actor, result)
        return response
    except MediaError as error:
        raise HTTPException(error.status, error.message) from error
    finally:
        await image.close()


class TranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    text: str
    language: str
    duration_seconds: float
    recognizer: str
    model_revision: str
    inference_ms: float
    model_load_ms: float
    warnings: list[str]
    suggestions: list[str] = Field(default_factory=list)


@router.post("/voice", response_model=TranscriptResponse)
async def search_voice(
    service: Annotated[SpeechService, Depends(speech_service)], audio: Annotated[UploadFile, File()]
) -> TranscriptResponse:
    try:
        result = await service.transcribe(
            await audio.read(2 * 1024 * 1024 + 1), audio.content_type or "", audio.filename or ""
        )
        return TranscriptResponse.model_validate(result)
    except MediaError as error:
        raise HTTPException(error.status, error.message) from error
    finally:
        await audio.close()
