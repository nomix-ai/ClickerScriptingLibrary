import json
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
        value = self.config.get(key, default)
        return str(value)

    def _load_config(self) -> None:
        try:
            self.config = json.loads(self.config_path.read_text())
            self.last_reload_time = time.time()
        except FileNotFoundError:
            self.config = {}
            self.last_reload_time = time.time()

    def _check_reload(self) -> None:
        if time.time() - self.last_reload_time > self.reload_interval_seconds:
            self._load_config()
