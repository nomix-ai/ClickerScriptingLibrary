from pathlib import Path

from .config_handler import ConfigHandler

config_path = Path(__file__).parent.parent / 'config.json'
config = ConfigHandler(config_path)

API_URL = config.get('API_URL', 'https://panel.nomixclicker.com/clicker/v1')
API_KEY = config.get('API_KEY', '')
DEVICE_ID = config.get('DEVICE_ID', 'your-device-id')