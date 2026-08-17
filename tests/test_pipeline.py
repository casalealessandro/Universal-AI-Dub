import asyncio
from collections.abc import AsyncIterator

import pytest

from src.ai.stt import SpeechRecognizer, TranscriptEvent
from src.ai.translator import Translator
from src.ai.tts import AudioStream, SpeechSynthesizer
from src.audio.sink import AudioSink
from src.audio.source import AudioChunk, AudioSource
from src.pipeline.dub_pipeline import DubPipeline
from src.pipeline.metrics import Metrics


class FakeSource(AudioSource):
    async def _stream(self):
        yield AudioChunk(b"audio", 1.0, 16000)
    def stream(self) -> AsyncIterator[AudioChunk]:
        return self._stream()


class FakeRecognizer(SpeechRecognizer):
    async def _recognize(self):
        yield TranscriptEvent("hel", False, 1.0, 1.1)
        yield TranscriptEvent("hello", True, 1.0, 1.2)
    def recognize(self, chunks, language):  # noqa: ANN001
        return self._recognize()


class FakeTranslator(Translator):
    async def translate(self, text, source_language, target_language):  # noqa: ANN001
        return "ciao"


class FakeTTS(SpeechSynthesizer):
    async def synthesize(self, text, language):  # noqa: ANN001
        async def chunks():
            yield b"pcm"
        return AudioStream(chunks())


class FakeSink(AudioSink):
    async def play(self, audio, sample_rate):  # noqa: ANN001
        async for _ in audio:
            pass
        import time
        return time.monotonic()


def test_pipeline_uses_only_final_transcript():
    partials, segments, metrics = [], [], Metrics()
    pipeline = DubPipeline(FakeSource(), FakeRecognizer(), FakeTranslator(), FakeTTS(), FakeSink(), metrics,
                           lambda event: partials.append(event.text), lambda source, target, timing: segments.append((source, target)))
    asyncio.run(pipeline.run("en", "it"))
    assert partials == ["hel"]
    assert segments == [("hello", "ciao")]
    assert len(metrics.segments) == 1


def test_components_are_abstract():
    for component in (AudioSource, SpeechRecognizer, Translator, SpeechSynthesizer, AudioSink):
        with pytest.raises(TypeError):
            component()
