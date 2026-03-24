from __future__ import annotations

import httpx

from pls.providers import ProviderError


class LMStudioProvider:
    def __init__(self, host: str = "http://localhost:1234", model: str = ""):
        self.host = host.rstrip("/")
        self.model = model

    def generate(self, system_prompt: str, user_message: str) -> str:
        url = f"{self.host}/v1/chat/completions"
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
        try:
            response = httpx.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.ConnectError:
            raise ProviderError(
                f"Cannot connect to LM Studio at {self.host}. Make sure LM Studio is running with the local server enabled."
            )
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"LM Studio error: {e.response.status_code} — {e.response.text}")
        except (KeyError, IndexError):
            raise ProviderError("Unexpected response format from LM Studio")
        except httpx.TimeoutException:
            raise ProviderError("LM Studio request timed out.")
