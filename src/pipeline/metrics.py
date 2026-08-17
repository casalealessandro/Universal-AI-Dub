from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SegmentMetrics:
    audio_received_at: float
    stt_completed_at: float
    translation_completed_at: float
    tts_first_audio_at: float
    playback_started_at: float

    @property
    def stt_latency_ms(self) -> float:
        return (self.stt_completed_at - self.audio_received_at) * 1000

    @property
    def translation_latency_ms(self) -> float:
        return (self.translation_completed_at - self.stt_completed_at) * 1000

    @property
    def tts_latency_ms(self) -> float:
        return (self.tts_first_audio_at - self.translation_completed_at) * 1000

    @property
    def total_latency_ms(self) -> float:
        return (self.playback_started_at - self.audio_received_at) * 1000


class Metrics:
    def __init__(self) -> None:
        self.segments: list[SegmentMetrics] = []

    def add(self, segment: SegmentMetrics) -> None:
        self.segments.append(segment)

    def summary(self) -> dict[str, float | int]:
        totals = [item.total_latency_ms for item in self.segments]
        if not totals:
            return {"count": 0, "average_ms": 0.0, "minimum_ms": 0.0, "maximum_ms": 0.0}
        return {"count": len(totals), "average_ms": sum(totals) / len(totals), "minimum_ms": min(totals), "maximum_ms": max(totals)}
