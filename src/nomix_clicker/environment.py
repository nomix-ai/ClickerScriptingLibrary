import os
import sys
from pathlib import Path

from .config_handler import ConfigHandler

DEFAULT_API_URL = "https://panel.nomixclicker.com/clicker/v1"

# Config priority (highest first): NOMIX_* env vars, then config.json, then
# built-in defaults. The path is resolved once at import so the 300s
# auto-reload survives a later os.chdir().


def _find_config_path() -> Path:
    override = os.environ.get("NOMIX_CONFIG")
    if override:
        return Path(override).resolve()
    # cwd first, then next to the entry script and one level up,
    # so the in-repo tools/ and examples/ scripts work from any cwd
    candidates = [Path.cwd() / "config.json"]
    if sys.argv and sys.argv[0]:
        script_dir = Path(sys.argv[0]).resolve().parent
        candidates += [script_dir / "config.json", script_dir.parent / "config.json"]
    # editable installs: <repo>/src/nomix_clicker/environment.py -> <repo>/config.json
    candidates.append(Path(__file__).resolve().parents[2] / "config.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


_config_path = _find_config_path()
config = ConfigHandler(_config_path)


def _resolve(key: str, default: str = "") -> str:
    """Resolve a config value: env var wins, then config.json, then default."""
    env_value = os.environ.get(f"NOMIX_{key}")
    if env_value:
        return env_value
    return config.get(key, default)  # falsy config values fall back to the default


def get_api_url() -> str:
    return _resolve("API_URL", DEFAULT_API_URL)


def get_api_key() -> str:
    return _resolve("API_KEY", "")


def get_device_id() -> str:
    return _resolve("DEVICE_ID", "")


# Import-time snapshots; API calls use the live get_* functions above.
API_URL = get_api_url()
API_KEY = get_api_key()
DEVICE_ID = get_device_id()

_missing = [name for name, value in (("API_KEY", API_KEY), ("DEVICE_ID", DEVICE_ID)) if not value]
if _missing:
    _where = f"config file {_config_path.resolve()}"
    if not _config_path.exists():
        _where += " (not found)"
    print(
        f"WARNING: {', '.join(_missing)} not set — checked NOMIX_* env vars and {_where}. "
        "API calls will fail.",
        file=sys.stderr,
    )
