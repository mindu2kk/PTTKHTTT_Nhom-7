"""Bounded local decoding. Flush the resampler so the end of a spoken word survives."""

import io

import av
import numpy as np
from fastapi import HTTPException

SAMPLE_RATE = 16000
MAX_SAMPLES = 15 * SAMPLE_RATE
FORMATS = {"wav", "ogg", "matroska,webm", "mov,mp4,m4a,3gp,3g2,mj2"}


def decode_audio(raw: bytes) -> np.ndarray:
    chunks: list[np.ndarray] = []
    count = 0

    def append_frames(frames):
        nonlocal count
        for frame in frames:
            samples = frame.to_ndarray().flatten().astype(np.float32) / 32768
            count += len(samples)
            if count > MAX_SAMPLES:
                raise HTTPException(
                    422, "Bản ghi tối đa 15 giây. Hãy ghi một câu ngắn hơn."
                )
            chunks.append(samples)

    try:
        with av.open(
            io.BytesIO(raw),
            options={"protocol_whitelist": "pipe", "enable_drefs": "0"},
        ) as container:
            if container.streams.video or not container.streams.audio:
                raise HTTPException(422, "Chỉ nhận tệp âm thanh, không nhận video.")
            if container.format.name not in FORMATS:
                raise HTTPException(422, "Định dạng âm thanh chưa được hỗ trợ.")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
            for frame in container.decode(audio=0):
                append_frames(resampler.resample(frame))
            # libswresample buffers the filter tail when the sample rates differ.
            # EOF is not an implicit flush; account for these samples in the same limit.
            append_frames(resampler.resample(None))
        if not chunks:
            raise HTTPException(422, "Không tìm thấy âm thanh trong tệp.")
        audio = np.concatenate(chunks)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(422, "Tệp âm thanh bị hỏng hoặc không đọc được.") from error
    if len(audio) < 1600 or float(np.mean(audio**2)) < 1e-6:
        raise HTTPException(422, "Không nghe rõ lời nói. Hãy ghi lại gần micro hơn.")
    return audio
