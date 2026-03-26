"""Anthropic AI LLM provider implementation."""

from __future__ import annotations

from pls.providers import ProviderError

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider:
    """Provider class for the Anthropic API."""
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    def generate(self, system_prompt: str, user_message: str) -> str:
        """Generate a response using the Anthropic API."""
        import httpx

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    ANTHROPIC_API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": user_message},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 512,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"].strip()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ProviderError("Invalid Anthropic API key.") from e
            if e.response.status_code == 429:
                raise ProviderError("Anthropic rate limit hit. Wait a moment and try again.") from e
            raise ProviderError(f"Anthropic error: {e.response.status_code} — {e.response.text}") from e
        except (KeyError, IndexError) as exc:
            raise ProviderError("Unexpected response format from Anthropic") from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("Anthropic request timed out.") from exc
