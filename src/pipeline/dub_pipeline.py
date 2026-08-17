from __future__ import annotations

import logging
import time
from collections.abc import Callable

from src.ai.stt import SpeechRecognizer, TranscriptEvent
from src.ai.translator import Translator
from src.ai.tts import SpeechSynthesizer
from src.audio.sink import AudioSink
from src.audio.source import AudioSource
from src.pipeline.metrics import Metrics, SegmentMetrics

logger = logging.getLogger(__name__)


class DubPipeline:
    def __init__(self, source: AudioSource, recognizer: SpeechRecognizer, translator: Translator,
                 synthesizer: SpeechSynthesizer, sink: AudioSink, metrics: Metrics,
                 on_partial: Callable[[TranscriptEvent], None] | None = None,
                 on_segment: Callable[[str, str, SegmentMetrics], None] | None = None) -> None:
        self.source, self.recognizer, self.translator = source, recognizer, translator
        self.synthesizer, self.sink, self.metrics = synthesizer, sink, metrics
        self.on_partial, self.on_segment = on_partial, on_segment

    async def run(self, input_language: str, output_language: str) -> None:
        try:
            async for event in self.recognizer.recognize(self.source.stream(), input_language):
                if not event.is_final:
                    if self.on_partial:
                        self.on_partial(event)
                    continue
                logger.debug("Final transcript: %s", event.text)
                try:
                    translated = await self.translator.translate(event.text, input_language, output_language)
                    translated_at = time.monotonic()
                    audio = await self.synthesizer.synthesize(translated, output_language)
                    first_audio_at: float | None = None

                    async def measured_audio():
                        nonlocal first_audio_at
                        async for chunk in audio.chunks:
                            if first_audio_at is None:
                                first_audio_at = time.monotonic()
                            yield chunk

                    playback_at = await self.sink.play(measured_audio(), audio.sample_rate)
                    segment = SegmentMetrics(event.audio_received_at, event.completed_at, translated_at,
                                             first_audio_at or playback_at, playback_at)
                    self.metrics.add(segment)
                    if self.on_segment:
                        self.on_segment(event.text, translated, segment)
                except Exception as exc:
                    logger.error("Segmento ignorato: %s", exc, exc_info=logger.isEnabledFor(logging.DEBUG))
        finally:
            await self.source.close()
            await self.sink.close()
