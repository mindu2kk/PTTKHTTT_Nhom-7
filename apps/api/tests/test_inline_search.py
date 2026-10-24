import unicodedata

import pytest

from app.application.speech import SpeechService
from app.domain.media import MediaError, Transcript


class Recognizer:
    def __init__(self, text):
        self.text = text

    async def transcribe(self, content, mime, filename):
        return Transcript(self.text, "vi", 1.0, "test-only", "test-only", 0, 0, ())


async def test_voice_search_text_is_nfc_trimmed_without_losing_words():
    text = unicodedata.normalize("NFD", "  Tôi  muốn\n mua giày  ")
    result = await SpeechService(Recognizer(text)).transcribe(b"fake", "audio/wav", "fake.wav")
    assert result.text == "Tôi muốn mua giày"
    assert unicodedata.is_normalized("NFC", result.text)


@pytest.mark.parametrize("text", ["", " \n\t ", "x" * 301])
async def test_voice_rejects_unsearchable_or_too_long_transcript(text):
    with pytest.raises(MediaError) as caught:
        await SpeechService(Recognizer(text)).transcribe(b"fake", "audio/wav", "fake.wav")
    assert caught.value.status == 422


@pytest.mark.parametrize("q", [" ", "\n\t", " " * 300])
async def test_text_search_rejects_blank_after_strip(client, q):
    response = await client.post("/api/v1/search/text", json={"q": q})
    assert response.status_code == 422


async def test_voice_and_text_keep_same_filtered_search_path(client):
    body = {"q": "  áo len nam dưới 500k  ", "page_size": 24}
    text = (await client.post("/api/v1/search/text", json=body)).json()
    voice = (await client.post("/api/v1/search/text", json={**body, "modality": "voice"})).json()
    assert text["items"] and voice["query"]["modality"] == "voice"
    assert voice["query"]["raw_text"] == body["q"].strip()
    assert [p["product"]["id"] for p in text["items"]] == [
        p["product"]["id"] for p in voice["items"]
    ]
    assert voice["query"]["hard_filters"] == text["query"]["hard_filters"]
