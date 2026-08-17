from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator

from src.audio.source import AudioChunk, AudioSource

logger = logging.getLogger(__name__)


class MicrophoneError(RuntimeError):
    pass


class MicrophoneSource(AudioSource):
    def __init__(self, sample_rate: int = 16_000, chunk_ms: int = 100, device: int | str | None = None) -> None:
        self.sample_rate = sample_rate
        self.chunk_ms = chunk_ms
        self.device = device
        self._stream = None
        self._queue: asyncio.Queue[AudioChunk | Exception] | None = None

    async def _chunks(self) -> AsyncIterator[AudioChunk]:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise MicrophoneError("sounddevice non installato: esegui pip install -r requirements.txt") from exc

        loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=100)

        def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
            if status:
                logger.warning("Microfono: %s", status)
            chunk = AudioChunk(bytes(indata), time.monotonic(), self.sample_rate)

            def enqueue() -> None:
                assert self._queue is not None
                if self._queue.full():
                    self._queue.get_nowait()
                    logger.warning("Buffer microfono pieno: chunk meno recente scartato")
                self._queue.put_nowait(chunk)

            loop.call_soon_threadsafe(enqueue)

        try:
            self._stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=int(self.sample_rate * self.chunk_ms / 1000),
                device=self.device,
                channels=1,
                dtype="int16",
                callback=callback,
            )
            self._stream.start()
        except Exception as exc:
            raise MicrophoneError(f"Microfono non disponibile: {exc}") from exc

        logger.info("Microfono attivo: %d Hz, chunk %d ms", self.sample_rate, self.chunk_ms)
        try:
            while True:
                item = await self._queue.get()
                if isinstance(item, Exception):
                    raise item
                logger.debug("Chunk audio: %d byte, timestamp=%.6f, buffer=%d", len(item.data), item.received_at, self._queue.qsize())
                yield item
        finally:
            await self.close()

    def stream(self) -> AsyncIterator[AudioChunk]:
        return self._chunks()

    async def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

