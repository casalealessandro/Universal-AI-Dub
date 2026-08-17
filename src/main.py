from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from src.ai.stt import DeepgramSpeechRecognizer
from src.ai.translator import DeepLTranslator
from src.ai.tts import ElevenLabsSpeechSynthesizer
from src.audio.microphone_source import MicrophoneSource
from src.audio.sink import SpeakerSink
from src.config import Config, ConfigurationError
from src.pipeline.dub_pipeline import DubPipeline
from src.pipeline.metrics import Metrics, SegmentMetrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Universal AI Dub near-real-time POC")
    parser.add_argument("--source", choices=["microphone"], default="microphone")
    parser.add_argument("--input-language", default="en")
    parser.add_argument("--output-language", default="it")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        config = Config.from_env()
    except ConfigurationError as exc:
        logging.error("Configurazione non valida: %s", exc)
        return 2

    metrics = Metrics()
    print(f"Universal AI Dub\n\nInput language:  {args.input_language}\nOutput language: {args.output_language}\n\nListening...", flush=True)

    def partial(event) -> None:  # noqa: ANN001
        logging.debug("Partial transcript: %s (timestamp=%.6f)", event.text, event.completed_at)

    def segment(original: str, translated: str, timing: SegmentMetrics) -> None:
        print(f"\n[{args.input_language.upper()}] {original}\n[{args.output_language.upper()}] {translated}\n\n"
              f"STT:         {timing.stt_latency_ms:7.0f} ms\nTranslation: {timing.translation_latency_ms:7.0f} ms\n"
              f"TTS:         {timing.tts_latency_ms:7.0f} ms\nTotal:       {timing.total_latency_ms:7.0f} ms", flush=True)

    pipeline = DubPipeline(MicrophoneSource(chunk_ms=config.chunk_ms),
        DeepgramSpeechRecognizer(config.deepgram_api_key, timeout=config.provider_timeout_seconds),
        DeepLTranslator(config.deepl_api_key, config.deepl_base_url, config.provider_timeout_seconds),
        ElevenLabsSpeechSynthesizer(config.elevenlabs_api_key, config.elevenlabs_voice_id, timeout=config.provider_timeout_seconds),
        SpeakerSink(), metrics, partial, segment)
    try:
        await pipeline.run(args.input_language, args.output_language)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logging.error("Pipeline interrotta: %s", exc, exc_info=args.debug)
        return 1
    finally:
        summary = metrics.summary()
        print(f"\nSession summary\nTranslated segments: {summary['count']}\nAverage latency: {summary['average_ms']:.0f} ms\n"
              f"Minimum latency: {summary['minimum_ms']:.0f} ms\nMaximum latency: {summary['maximum_ms']:.0f} ms")
    return 0


def main() -> None:
    try:
        raise SystemExit(asyncio.run(async_main()))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
