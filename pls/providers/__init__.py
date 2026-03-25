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

    elif name in ("openai", "lmstudio", "llamacpp"):
        from pls.providers.openai import OpenAIProvider
        from pls.config import get_api_key, get_model

        defaults = {
            "openai": ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
            "lmstudio": ("http://localhost:1234/v1/chat/completions", "unknown"),
            "llamacpp": ("http://localhost:8080/v1/chat/completions", "unknown"),
        }
        default_url, default_model = defaults[name]

        api_key = get_api_key(config, name) or "not-needed"
        model = get_model(config, name) or default_model
        api_url = config.get(name, {}).get("api_url") or default_url

        return OpenAIProvider(api_key=api_key, model=model, api_url=api_url)

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

    else:
        # Fallback for any unknown provider or 'custom'
        from pls.providers.openai import OpenAIProvider
        from pls.config import get_api_key, get_model

        # The maintainer added 'custom' section, let's support it too
        section = "custom" if name == "custom" else name
        api_url = config.get(section, {}).get("api_url") or config.get(section, {}).get("url")
        
        if not api_url:
            raise ProviderError(
                f"Unknown provider: {name}. Available presets: ollama, openai, lmstudio, llamacpp, anthropic.\n"
                f"To use '{name}', set its API URL: pls config set {name} api_url <url>"
            )

        api_key = get_api_key(config, section) or "not-needed"
        model = get_model(config, section) or "unknown"
        return OpenAIProvider(api_key=api_key, model=model, api_url=api_url)
