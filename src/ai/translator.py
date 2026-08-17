from __future__ import annotations

from abc import ABC, abstractmethod

class Translator(ABC):
    @abstractmethod
    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        import httpx

        raise NotImplementedError


class DeepLTranslator(Translator):
    def __init__(self, api_key: str, base_url: str = "https://api-free.deepl.com", timeout: float = 15.0) -> None:
        self.api_key, self.base_url, self.timeout = api_key, base_url.rstrip("/"), timeout

    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/v2/translate", headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                                             data={"text": text, "source_lang": source_language.upper(), "target_lang": target_language.upper()})
                response.raise_for_status()
            return response.json()["translations"][0]["text"]
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            raise RuntimeError(f"Errore traduzione DeepL: {exc}") from exc
