import json
import sys
import time
from pathlib import Path
from typing import Any


class ConfigHandler:

    def __init__(self, config_path: Path, reload_interval: int = 300):
        self.config_path = config_path
        self.reload_interval_seconds = reload_interval
        self.last_reload_time = 0
        self.config = {}
        self._load_config()

    def get(self, key: str, default: Any = '') -> str:
        self._check_reload()
        value = self.config.get(key)
        if not value:  # missing key or a null/false/0/"" value — use the default
            value = default
        return str(value)

    def _load_config(self) -> None:
        try:
            data = json.loads(self.config_path.read_text())
            if not isinstance(data, dict):
                print(f"WARNING: {self.config_path} must contain a JSON object", file=sys.stderr)
                data = {}
            self.config = data
        except FileNotFoundError:
            self.config = {}
        except json.JSONDecodeError as e:
            print(f"WARNING: Invalid JSON in {self.config_path}: {e}", file=sys.stderr)
            self.config = {}
        except OSError as e:
            print(f"WARNING: Cannot read {self.config_path}: {e}", file=sys.stderr)
            self.config = {}
        self.last_reload_time = time.monotonic()

    def _check_reload(self) -> None:
        if time.monotonic() - self.last_reload_time > self.reload_interval_seconds:
            self._load_config()
