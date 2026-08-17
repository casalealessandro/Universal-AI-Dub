from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass(frozen=True, slots=True)
class AudioChunk:
    data: bytes
    received_at: float
    sample_rate: int
    channels: int = 1


class AudioSource(ABC):
    @abstractmethod
    def stream(self) -> AsyncIterator[AudioChunk]:
        """Return a continuous stream of signed 16-bit little-endian PCM chunks."""
        raise NotImplementedError

    async def close(self) -> None:
        """Release source resources."""

