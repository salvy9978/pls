from __future__ import annotations

import httpx

from pls.providers import ProviderError

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        api_url: str = "https://api.openai.com/v1/chat/completions",
    ):
        self.api_key = api_key
        self.model = model
        self.api_url = self._normalize_url(api_url)

    def _normalize_url(self, url: str) -> str:
        url = url.rstrip("/")
        if url.endswith("/v1/chat/completions"):
            return url
        if url.endswith("/v1"):
            return f"{url}/chat/completions"
        return f"{url}/v1/chat/completions"

    def generate(self, system_prompt: str, user_message: str) -> str:
        try:
            response = httpx.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 512,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ProviderError(f"Invalid API key for {self.api_url}")
            if e.response.status_code == 429:
                raise ProviderError(f"Rate limit hit for {self.api_url}. Wait a moment and try again.")
            raise ProviderError(f"API error from {self.api_url}: {e.response.status_code} — {e.response.text}")
        except (KeyError, IndexError):
            raise ProviderError(f"Unexpected response format from {self.api_url}")
        except httpx.TimeoutException:
            raise ProviderError(f"Request to {self.api_url} timed out.")
