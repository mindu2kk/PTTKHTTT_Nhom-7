"""Actual PCM/PyAV boundary tests, no model files, database or network required."""

import io
import unittest
import wave

import numpy as np
from fastapi import HTTPException

from audio_decode import decode_audio


def wav(rate=16000, duration=1, channels=1, silent=False):
    samples = int(rate * duration)
    values = np.zeros(samples) if silent else np.sin(np.arange(samples) * 1000 / rate)
    pcm = (values * 16000).astype("<i2")
    if channels == 2:
        pcm = np.repeat(pcm[:, None], 2, axis=1).flatten()
    target = io.BytesIO()
    with wave.open(target, "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(pcm.tobytes())
    return target.getvalue()


class DecodeTests(unittest.TestCase):
    def test_16k_is_not_resampled_or_normalized(self):
        raw = wav()
        with wave.open(io.BytesIO(raw)) as stream:
            expected = np.frombuffer(stream.readframes(16000), dtype="<i2") / 32768
        np.testing.assert_array_equal(decode_audio(raw), expected.astype(np.float32))

    def test_resampler_flush_keeps_all_48k_samples(self):
        self.assertEqual(len(decode_audio(wav(48000))), 16000)

    def test_stereo_to_mono_and_44100_resampling(self):
        audio = decode_audio(wav(44100, channels=2))
        self.assertEqual(len(audio), 16000)
        self.assertEqual(audio.dtype, np.float32)
        self.assertTrue(np.isfinite(audio).all())

    def test_boundary_15_seconds_48k_includes_flushed_tail(self):
        self.assertEqual(len(decode_audio(wav(48000, 15))), 240000)
        with self.assertRaises(HTTPException) as caught:
            decode_audio(wav(48000, 15.01))
        self.assertEqual(caught.exception.status_code, 422)

    def test_corrupt_audio_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            decode_audio(b"not audio")
        self.assertEqual(caught.exception.status_code, 422)

    def test_silence_is_rejected_without_model(self):
        with self.assertRaises(HTTPException) as caught:
            decode_audio(wav(silent=True))
        self.assertEqual(caught.exception.status_code, 422)

    def test_short_audio_is_rejected_without_model(self):
        with self.assertRaises(HTTPException) as caught:
            decode_audio(wav(duration=0.09))
        self.assertEqual(caught.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
