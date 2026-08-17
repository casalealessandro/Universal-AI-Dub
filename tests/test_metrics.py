import pytest

from src.pipeline.metrics import Metrics, SegmentMetrics


def test_segment_latencies_and_summary():
    segment = SegmentMetrics(1.0, 1.4, 1.5, 1.8, 1.9)
    assert round(segment.stt_latency_ms) == 400
    assert round(segment.translation_latency_ms) == 100
    assert round(segment.tts_latency_ms) == 300
    metrics = Metrics()
    metrics.add(segment)
    summary = metrics.summary()
    assert summary["count"] == 1
    assert summary["average_ms"] == pytest.approx(900.0)
    assert summary["minimum_ms"] == pytest.approx(900.0)
    assert summary["maximum_ms"] == pytest.approx(900.0)


def test_empty_summary():
    assert Metrics().summary()["count"] == 0
