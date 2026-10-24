import httpx
import pytest

from app.domain.media import MediaError
from app.infrastructure.media import SPEECH_MODELS, HttpSpeechRecognizer


def payload(revision, recognizer):
    return {
        "text": "tìm tai nghe",
        "language": "vi",
        "duration_seconds": 2.0,
        "recognizer": recognizer,
        "model_revision": revision,
        "inference_ms": 100,
        "model_load_ms": 0,
        "warnings": ["Kiểm tra câu đã nhận."],
    }


def mock_client(monkeypatch, data, status=200):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=data))
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs)
    )


@pytest.mark.parametrize("revision,recognizer", SPEECH_MODELS.items())
async def test_only_pinned_local_profiles_are_accepted(monkeypatch, revision, recognizer):
    mock_client(monkeypatch, payload(revision, recognizer))
    result = await HttpSpeechRecognizer("http://local-worker").transcribe(
        b"RIFF0000WAVE", "audio/wav", "x.wav"
    )
    assert (result.text, result.model_revision, result.recognizer) == (
        "tìm tai nghe",
        revision,
        recognizer,
    )


@pytest.mark.parametrize(
    "change",
    [
        {"model_revision": "unknown"},
        {"recognizer": "cloud-service"},
        {"model_revision": []},
        {"language": "en"},
        {"duration_seconds": "NaN"},
        {"duration_seconds": 16},
        {"text": ["tìm tai nghe"]},
        {"warnings": "not a list"},
        {"model_load_ms": -1},
        {"inference_ms": "Infinity"},
    ],
)
async def test_untrusted_or_malformed_worker_response_is_not_exposed(monkeypatch, change):
    revision, name = next(iter(SPEECH_MODELS.items()))
    mock_client(monkeypatch, {**payload(revision, name), **change})
    with pytest.raises(MediaError) as caught:
        await HttpSpeechRecognizer("http://local-worker").transcribe(
            b"RIFF0000WAVE", "audio/wav", "x.wav"
        )
    assert caught.value.status == 503


async def test_worker_429_is_not_hidden_as_a_successful_transcript(monkeypatch):
    mock_client(monkeypatch, {"detail": "Máy đang bận."}, 429)
    with pytest.raises(MediaError) as caught:
        await HttpSpeechRecognizer("http://local-worker").transcribe(
            b"RIFF0000WAVE", "audio/wav", "x.wav"
        )
    assert caught.value.status == 429
