"""HTTP contracts and real test-DB retrieval, separate from the offline unit suite."""

import pytest

from app.application.speech import SpeechService
from app.core.dependencies import speech_service
from app.domain.media import Transcript
from app.main import app


@pytest.mark.parametrize(
    "phrase,expected,operator",
    [
        ("áo len nam dưới năm trăm năm mươi nghìn", 550000, "lt"),
        ("áo len nam không quá một triệu hai trăm nghìn", 1200000, "lte"),
        ("áo len nam dưới 500.000 đồng", 500000, "lt"),
    ],
)
async def test_complete_spoken_price_reaches_filtered_catalog(client, phrase, expected, operator):
    response = await client.post("/api/v1/search/text", json={"q": phrase, "modality": "voice"})
    assert response.status_code == 200
    data = response.json()
    constraint = next(c for c in data["query"]["hard_filters"] if c["key"] == "price_max")
    assert (constraint["value"], constraint["operator"]) == (expected, operator)
    assert data["items"]
    assert all(r["product"]["price_vnd"] <= expected - (operator == "lt") for r in data["items"])


async def test_voice_contract_keeps_original_and_opt_in_alternative(client):
    class Recognizer:
        async def transcribe(self, content, mime, filename):
            return Transcript(
                "tìm tài nghe dưới 500k",
                "vi",
                2,
                "test-only",
                "test-only",
                0,
                0,
                ("Chưa chắc chắn.",),
            )

    app.dependency_overrides[speech_service] = lambda: SpeechService(Recognizer())
    try:
        response = await client.post(
            "/api/v1/search/voice",
            files={"audio": ("test.wav", b"fake-for-contract-only", "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "tìm tài nghe dưới 500k"
        assert data["suggestions"] == ["tìm tai nghe dưới 500k"]
        assert data["warnings"] == ["Chưa chắc chắn."]
    finally:
        app.dependency_overrides.pop(speech_service, None)
