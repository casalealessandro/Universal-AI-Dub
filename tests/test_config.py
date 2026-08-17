import pytest

from src.config import Config, ConfigurationError


KEYS = ["DEEPGRAM_API_KEY", "DEEPL_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"]


def test_config_requires_keys(monkeypatch):
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("src.config.load_dotenv", lambda: None)
    with pytest.raises(ConfigurationError, match="DEEPGRAM_API_KEY"):
        Config.from_env()


def test_config_loads(monkeypatch):
    monkeypatch.setattr("src.config.load_dotenv", lambda: None)
    for key in KEYS:
        monkeypatch.setenv(key, "test")
    assert Config.from_env().chunk_ms == 100
