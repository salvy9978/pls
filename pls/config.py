from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import json as tomllib

_FALLBACK_TOML = sys.version_info < (3, 11) and not hasattr(tomllib, "loads")

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pls"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG: dict[str, Any] = {
    "default": {
        "provider": "ollama",
        "model": "",
    },
    "ollama": {
        "host": "http://localhost:11434",
        "model": "llama3.2",
    },
    "openai": {
        "api_key": "",
        "model": "gpt-4o-mini",
    },
    "anthropic": {
        "api_key": "",
        "model": "claude-sonnet-4-20250514",
    },
}


def _parse_toml(text: str) -> dict[str, Any]:
    if not _FALLBACK_TOML:
        return tomllib.loads(text)
    result: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            result[section_name] = {}
            current_section = result[section_name]
        elif "=" in line and current_section is not None:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            current_section[key] = value
    return result


def _dump_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for section, values in data.items():
        if isinstance(values, dict):
            lines.append(f"[{section}]")
            for key, val in values.items():
                if isinstance(val, str):
                    lines.append(f'{key} = "{val}"')
                elif isinstance(val, bool):
                    lines.append(f"{key} = {'true' if val else 'false'}")
                else:
                    lines.append(f"{key} = {val}")
            lines.append("")
    return "\n".join(lines) + "\n"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        text = CONFIG_FILE.read_text(encoding="utf-8")
        user_config = _parse_toml(text)
        return _deep_merge(DEFAULT_CONFIG, user_config)
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(_dump_toml(config), encoding="utf-8")


def get_provider_name(config: dict[str, Any]) -> str:
    return config.get("default", {}).get("provider", "ollama")


def get_model(config: dict[str, Any], provider_name: str | None = None) -> str:
    if provider_name is None:
        provider_name = get_provider_name(config)

    default_model = config.get("default", {}).get("model", "")
    if default_model:
        return default_model
    return config.get(provider_name, {}).get("model", "")


def get_api_key(config: dict[str, Any], provider_name: str | None = None) -> str:
    if provider_name is None:
        provider_name = get_provider_name(config)

    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }

    env_var = env_map.get(provider_name, "")
    if env_var:
        env_value = os.environ.get(env_var, "")
        if env_value:
            return env_value
    return config.get(provider_name, {}).get("api_key", "")


def set_config_value(section: str, key: str, value: str) -> None:
    config = load_config()
    if section not in config:
        config[section] = {}
    config[section][key] = value
    save_config(config)
