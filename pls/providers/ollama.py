from __future__ import annotations

import httpx

from pls.providers import ProviderError


class OllamaProvider:
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.2"):
        self.host = host.rstrip("/")
        self.model = model

    def generate(self, system_prompt: str, user_message: str) -> str:
        try:
            response = httpx.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"].strip()
        except httpx.ConnectError:
            raise ProviderError(
                f"Cannot connect to Ollama at {self.host}. Is it running?\n"
                "Start it with: ollama serve"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ProviderError(
                    f"Model '{self.model}' not found. Pull it with: ollama pull {self.model}"
                )
            raise ProviderError(f"Ollama error: {e.response.status_code} — {e.response.text}")
        except KeyError:
            raise ProviderError("Unexpected response format from Ollama")
        except httpx.TimeoutException:
            raise ProviderError("Ollama request timed out. The model might be loading — try again.")
