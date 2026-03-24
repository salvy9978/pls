from __future__ import annotations

import httpx

from pls.providers import ProviderError


class CustomProvider:
    def __init__(self, url: str, model: str = "", api_key: str = ""):
        self.url = url.rstrip("/")
        self.model = model
        self.api_key = api_key

    def generate(self, system_prompt: str, user_message: str) -> str:
        endpoint = f"{self.url}/v1/chat/completions"
        payload: dict = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "max_tokens": 512,
        }
        if self.model:
            payload["model"] = self.model

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = httpx.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.ConnectError:
            raise ProviderError(f"Cannot connect to {self.url}. Is the server running?")
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"Server error: {e.response.status_code} — {e.response.text}")
        except (KeyError, IndexError):
            raise ProviderError("Unexpected response format from server")
        except httpx.TimeoutException:
            raise ProviderError("Request timed out.")
