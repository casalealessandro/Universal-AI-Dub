from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # Consente almeno diagnostica/configurazione senza extra installati.
    def load_dotenv() -> bool:
        return False


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Config:
    deepgram_api_key: str
    deepl_api_key: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    deepl_base_url: str = "https://api-free.deepl.com"
    provider_timeout_seconds: float = 15.0
    chunk_ms: int = 100

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        names = ["DEEPGRAM_API_KEY", "DEEPL_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"]
        missing = [name for name in names if not os.getenv(name)]
        if missing:
            raise ConfigurationError("Variabili d'ambiente mancanti: " + ", ".join(missing))
        try:
            timeout, chunk_ms = float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "15")), int(os.getenv("AUDIO_CHUNK_MS", "100"))
        except ValueError as exc:
            raise ConfigurationError("Timeout e dimensione chunk devono essere numerici") from exc
        if not 20 <= chunk_ms <= 1000 or timeout <= 0:
            raise ConfigurationError("AUDIO_CHUNK_MS deve essere 20..1000 e il timeout positivo")
        return cls(*(os.environ[name] for name in names), os.getenv("DEEPL_BASE_URL", "https://api-free.deepl.com"), timeout, chunk_ms)
