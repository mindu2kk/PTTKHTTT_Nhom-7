import pytest

from app.domain.media import MediaError
from app.infrastructure.media import HttpSpeechRecognizer, validate_audio


@pytest.mark.parametrize(
    "raw,mime,name",
    [
        (b"RIFF0000WAVE", "audio/wav", "x.wav"),
        (b"OggS0000", "audio/ogg;codecs=opus", "x.ogg"),
        (b"\x1aE\xdf\xa3data", "audio/webm;codecs=opus", "x.webm"),
        (b"0000ftypdata", "audio/mp4", "x.m4a"),
    ],
    ids=["wav", "ogg", "webm", "m4a"],
)
def test_audio_container_whitelist(raw, mime, name):
    validate_audio(raw, mime, name)


@pytest.mark.parametrize(
    "raw,mime,name,status",
    [
        (b"bad", "audio/wav", "bad.wav", 422),
        (b"RIFF0000WAVE", "audio/wav", "bad.mp3", 422),
        (b"RIFF0000WAVE", "text/plain", "bad.wav", 422),
        (b"x" * (2 * 1024 * 1024 + 1), "audio/wav", "large.wav", 413),
    ],
    ids=["bad-magic", "wrong-extension", "wrong-mime", "oversized"],
)
def test_audio_rejects_invalid_envelope(raw, mime, name, status):
    with pytest.raises(MediaError) as error:
        validate_audio(raw, mime, name)
    assert error.value.status == status


async def test_asr_unavailable_has_text_fallback():
    with pytest.raises(MediaError) as error:
        await HttpSpeechRecognizer("http://127.0.0.1:1").transcribe(
            b"RIFF0000WAVE", "audio/wav", "x.wav"
        )
    assert error.value.status == 503 and "nhập văn bản" in error.value.message
