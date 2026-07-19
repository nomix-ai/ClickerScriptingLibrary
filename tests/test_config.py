"""Config resolution: env vars > config.json (cwd) > built-in defaults."""

import json

from nomix_clicker import environment
from nomix_clicker.config_handler import ConfigHandler


def test_config_handler_reads_json(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"API_KEY": "from-file", "DEVICE_ID": "dev-1"}))
    handler = ConfigHandler(cfg)
    assert handler.get("API_KEY") == "from-file"
    assert handler.get("DEVICE_ID") == "dev-1"


def test_config_handler_missing_file_uses_default(tmp_path):
    handler = ConfigHandler(tmp_path / "does-not-exist.json")
    assert handler.get("API_KEY", "fallback") == "fallback"


def test_config_handler_invalid_json_uses_default(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text("{ not valid json ]")
    handler = ConfigHandler(cfg)
    assert handler.get("API_KEY", "fallback") == "fallback"


def test_resolve_prefers_env_over_config(monkeypatch, tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"API_KEY": "from-file"}))
    monkeypatch.setattr(environment, "config", ConfigHandler(cfg))
    monkeypatch.setenv("NOMIX_API_KEY", "from-env")
    assert environment._resolve("API_KEY", "default") == "from-env"


def test_resolve_falls_back_to_config(monkeypatch, tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"API_KEY": "from-file"}))
    monkeypatch.setattr(environment, "config", ConfigHandler(cfg))
    monkeypatch.delenv("NOMIX_API_KEY", raising=False)
    assert environment._resolve("API_KEY", "default") == "from-file"


def test_resolve_falls_back_to_default(monkeypatch, tmp_path):
    monkeypatch.setattr(environment, "config", ConfigHandler(tmp_path / "none.json"))
    monkeypatch.delenv("NOMIX_API_URL", raising=False)
    assert environment._resolve("API_URL", "the-default") == "the-default"


def test_empty_env_var_does_not_shadow_config(monkeypatch, tmp_path):
    # An empty NOMIX_* var should not win over a real config value.
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"API_KEY": "from-file"}))
    monkeypatch.setattr(environment, "config", ConfigHandler(cfg))
    monkeypatch.setenv("NOMIX_API_KEY", "")
    assert environment._resolve("API_KEY", "default") == "from-file"


def test_null_false_and_empty_values_fall_back_to_default(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"A": None, "B": False, "C": ""}))
    handler = ConfigHandler(cfg)
    assert handler.get("A", "d") == "d"
    assert handler.get("B", "d") == "d"
    assert handler.get("C", "d") == "d"


def test_unreadable_config_degrades_to_empty(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "config.json"
    cfg.write_text("{}")
    def deny(self, *a, **k):
        raise PermissionError("denied")

    monkeypatch.setattr(type(cfg), "read_text", deny)
    handler = ConfigHandler(cfg)
    assert handler.get("API_KEY", "fallback") == "fallback"
    assert "Cannot read" in capsys.readouterr().err


def test_non_object_config_degrades_to_empty(tmp_path, capsys):
    cfg = tmp_path / "config.json"
    cfg.write_text('["not", "a", "dict"]')
    handler = ConfigHandler(cfg)
    assert handler.get("API_KEY", "x") == "x"
    assert "JSON object" in capsys.readouterr().err


def test_environment_config_path_is_absolute():
    # reload must survive a later os.chdir()
    assert environment._config_path.is_absolute()


def test_empty_nomix_config_env_is_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("NOMIX_CONFIG", "")
    monkeypatch.chdir(tmp_path)
    assert environment._find_config_path().name == "config.json"
