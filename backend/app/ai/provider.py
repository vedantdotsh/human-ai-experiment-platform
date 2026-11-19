import logging
import os

import httpx

log = logging.getLogger("ai.provider")

API_URL = "https://api.mistral.ai/v1/chat/completions"


class ProviderError(Exception):
    """A call that failed for any reason. Never carries the key or the response body."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MistralProvider:
    """One LLM provider. The key and model stay on the backend."""

    def __init__(self, api_key: str, model: str) -> None:
        self._key = api_key
        self.model = model
        self._client = httpx.AsyncClient()

    async def complete(
        self, system: str, user: str, *, max_tokens: int, temperature: float, timeout: float
    ) -> str:
        try:
            response = await self._client.post(
                API_URL,
                headers={"Authorization": f"Bearer {self._key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=timeout,
            )
        except httpx.TimeoutException:
            raise ProviderError("timeout") from None
        except httpx.HTTPError as exc:
            raise ProviderError(f"network:{type(exc).__name__}") from None
        if response.status_code != 200:
            raise ProviderError(f"http_{response.status_code}")
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("bad_response") from None

    async def close(self) -> None:
        await self._client.aclose()


def provider_from_env(model: str) -> MistralProvider | None:
    key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not key:
        log.info("no MISTRAL_API_KEY set: AI players will use scripted lines only")
        return None
    return MistralProvider(key, model)
