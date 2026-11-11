from __future__ import annotations

from pls import config as config_mod


def test_load_config_returns_independent_copies(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CONFIG_FILE", tmp_path / "config.toml")

    first = config_mod.load_config()
    first["ollama"]["model"] = "mutated"
    first["default"]["provider"] = "mutated"

    second = config_mod.load_config()
    assert second["ollama"]["model"] == "qwen3.5:2b"
    assert second["default"]["provider"] == "ollama"
    assert config_mod.DEFAULT_CONFIG["ollama"]["model"] == "qwen3.5:2b"
    assert config_mod.DEFAULT_CONFIG["default"]["provider"] == "ollama"
