from __future__ import annotations

import httpx

from pls.providers import ProviderError

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def generate(self, system_prompt: str, user_message: str) -> str:
        try:
            response = httpx.post(
                OPENAI_API_URL,
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
                raise ProviderError("Invalid OpenAI API key.")
            if e.response.status_code == 429:
                raise ProviderError("OpenAI rate limit hit. Wait a moment and try again.")
            raise ProviderError(f"OpenAI error: {e.response.status_code} — {e.response.text}")
        except (KeyError, IndexError):
            raise ProviderError("Unexpected response format from OpenAI")
        except httpx.TimeoutException:
            raise ProviderError("OpenAI request timed out.")
