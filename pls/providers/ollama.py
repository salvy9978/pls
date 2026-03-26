"""Ollama local LLM provider implementation."""

from __future__ import annotations

from pls.providers import ProviderError


class OllamaProvider:
    """Provider class for local Ollama instances."""
    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen3.5:2b"):
        self.host = host.rstrip("/")
        self.model = model

    def generate(self, system_prompt: str, user_message: str) -> str:
        """Generate a response using Ollama."""
        import httpx

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
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
                )
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"].strip()
        except httpx.ConnectError as exc:
            raise ProviderError(
                f"Cannot connect to Ollama at {self.host}. Is it running?\n"
                "Start it with: ollama serve"
            ) from exc
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ProviderError(
                    f"Model '{self.model}' not found. Pull it with: ollama pull {self.model}"
                ) from e
            raise ProviderError(f"Ollama error: {e.response.status_code} — {e.response.text}") from e
        except KeyError as exc:
            raise ProviderError("Unexpected response format from Ollama") from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("Ollama request timed out. The model might be loading — try again.") from exc
