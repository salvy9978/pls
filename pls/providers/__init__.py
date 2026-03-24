from __future__ import annotations

from typing import Any, Protocol


class Provider(Protocol):
    def generate(self, system_prompt: str, user_message: str) -> str: ...


class ProviderError(Exception):
    pass


def get_provider(name: str, config: dict[str, Any]) -> Provider:
    if name == "ollama":
        from pls.providers.ollama import OllamaProvider

        host = config.get("ollama", {}).get("host", "http://localhost:11434")
        model = config.get("ollama", {}).get("model", "qwen3.5:2b")
        return OllamaProvider(host=host, model=model)

    elif name == "openai":
        from pls.providers.openai import OpenAIProvider
        from pls.config import get_api_key, get_model

        api_key = get_api_key(config, "openai")
        if not api_key:
            raise ProviderError(
                "OpenAI API key not found. Set OPENAI_API_KEY env var or run: pls config set openai api_key <key>"
            )
        model = get_model(config, "openai") or "gpt-4o-mini"
        return OpenAIProvider(api_key=api_key, model=model)

    elif name == "anthropic":
        from pls.providers.anthropic import AnthropicProvider
        from pls.config import get_api_key, get_model

        api_key = get_api_key(config, "anthropic")
        if not api_key:
            raise ProviderError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY env var or run: pls config set anthropic api_key <key>"
            )
        model = get_model(config, "anthropic") or "claude-sonnet-4-20250514"
        return AnthropicProvider(api_key=api_key, model=model)

    elif name == "lmstudio":
        from pls.providers.lmstudio import LMStudioProvider

        host = config.get("lmstudio", {}).get("host", "http://localhost:1234")
        model = config.get("lmstudio", {}).get("model", "")
        return LMStudioProvider(host=host, model=model)

    elif name == "custom":
        from pls.providers.custom import CustomProvider

        custom_cfg = config.get("custom", {})
        url = custom_cfg.get("url", "")
        if not url:
            raise ProviderError(
                "Custom provider URL not set. Run: pls config set custom url http://localhost:8080"
            )
        model = custom_cfg.get("model", "")
        api_key = custom_cfg.get("api_key", "")
        return CustomProvider(url=url, model=model, api_key=api_key)

    else:
        raise ProviderError(f"Unknown provider: {name}. Available: ollama, openai, anthropic, lmstudio, custom")
