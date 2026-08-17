from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class AudioSink(ABC):
    @abstractmethod
    async def play(self, audio: AsyncIterator[bytes], sample_rate: int) -> float:
        """Play PCM chunks and return the monotonic time playback started."""
        raise NotImplementedError

    async def close(self) -> None:
        """Release sink resources."""


class SpeakerSink(AudioSink):
    def __init__(self, device: int | str | None = None) -> None:
        self.device = device

    async def play(self, audio: AsyncIterator[bytes], sample_rate: int) -> float:
        import asyncio
        import time

        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("sounddevice non installato") from exc

        stream = None
        started_at: float | None = None
        try:
            async for chunk in audio:
                if stream is None:
                    stream = sd.RawOutputStream(samplerate=sample_rate, channels=1, dtype="int16", device=self.device)
                    stream.start()
                    started_at = time.monotonic()
                await asyncio.to_thread(stream.write, chunk)
        except Exception as exc:
            raise RuntimeError(f"Riproduzione audio non riuscita: {exc}") from exc
        finally:
            if stream is not None:
                await asyncio.to_thread(stream.stop)
                stream.close()
        if started_at is None:
            raise RuntimeError("Il provider TTS non ha restituito audio")
        return started_at

