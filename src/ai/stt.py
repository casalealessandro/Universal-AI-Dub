from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import monotonic
from urllib.parse import urlencode

from src.audio.source import AudioChunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TranscriptEvent:
    text: str
    is_final: bool
    audio_received_at: float
    completed_at: float


class SpeechRecognizer(ABC):
    @abstractmethod
    def recognize(self, chunks: AsyncIterator[AudioChunk], language: str) -> AsyncIterator[TranscriptEvent]:
        raise NotImplementedError


class DeepgramSpeechRecognizer(SpeechRecognizer):
    def __init__(self, api_key: str, model: str = "nova-3", timeout: float = 15.0) -> None:
        self.api_key, self.model, self.timeout = api_key, model, timeout

    async def _recognize(self, chunks: AsyncIterator[AudioChunk], language: str) -> AsyncIterator[TranscriptEvent]:
        import websockets

        params = urlencode({"model": self.model, "language": language, "encoding": "linear16", "sample_rate": 16000,
                            "channels": 1, "interim_results": "true", "smart_format": "true", "endpointing": 300,
                            "utterance_end_ms": 1000, "vad_events": "true"})
        uri = f"wss://api.deepgram.com/v1/listen?{params}"
        first_audio_at: float | None = None
        finalized_parts: list[str] = []

        async with websockets.connect(uri, extra_headers={"Authorization": f"Token {self.api_key}"}, open_timeout=self.timeout) as ws:
            async def send_audio() -> None:
                nonlocal first_audio_at
                async for chunk in chunks:
                    if first_audio_at is None:
                        first_audio_at = chunk.received_at
                    await ws.send(chunk.data)
                await ws.send(json.dumps({"type": "CloseStream"}))

            sender = asyncio.create_task(send_audio())
            try:
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                    except asyncio.TimeoutError as exc:
                        raise RuntimeError("Timeout del provider STT") from exc
                    message = json.loads(raw)
                    if message.get("type") == "Error":
                        raise RuntimeError(f"Errore Deepgram: {message.get('description', message)}")
                    if message.get("type") != "Results":
                        continue
                    text = message.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "").strip()
                    if not text:
                        continue
                    now = monotonic()
                    if message.get("is_final"):
                        finalized_parts.append(text)
                    if message.get("speech_final"):
                        final_text = " ".join(finalized_parts).strip()
                        if final_text:
                            yield TranscriptEvent(final_text, True, first_audio_at or now, now)
                        finalized_parts.clear()
                        first_audio_at = None
                    elif not message.get("is_final"):
                        preview = " ".join([*finalized_parts, text]).strip()
                        yield TranscriptEvent(preview, False, first_audio_at or now, now)
            finally:
                sender.cancel()
                await asyncio.gather(sender, return_exceptions=True)

    def recognize(self, chunks: AsyncIterator[AudioChunk], language: str) -> AsyncIterator[TranscriptEvent]:
        return self._recognize(chunks, language)
