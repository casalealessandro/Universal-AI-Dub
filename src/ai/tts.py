from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AudioStream:
    chunks: AsyncIterator[bytes]
    sample_rate: int = 24_000


class SpeechSynthesizer(ABC):
    @abstractmethod
    async def synthesize(self, text: str, language: str) -> AudioStream:
        raise NotImplementedError


class ElevenLabsSpeechSynthesizer(SpeechSynthesizer):
    def __init__(self, api_key: str, voice_id: str, model: str = "eleven_flash_v2_5", timeout: float = 20.0) -> None:
        self.api_key, self.voice_id, self.model, self.timeout = api_key, voice_id, model, timeout

    async def synthesize(self, text: str, language: str) -> AudioStream:
        async def chunks() -> AsyncIterator[bytes]:
            import httpx

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream("POST", url, params={"output_format": "pcm_24000"},
                                             headers={"xi-api-key": self.api_key, "accept": "audio/pcm"},
                                             json={"text": text, "model_id": self.model, "language_code": language}) as response:
                        response.raise_for_status()
                        async for data in response.aiter_bytes(chunk_size=4096):
                            if data:
                                yield data
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Errore TTS ElevenLabs: {exc}") from exc
        return AudioStream(chunks())
