from typing import Any, Dict, Optional
from pathlib import Path
import yaml


class Config:

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML config: {e}")

    def get(self, path: str, default: Any = None) -> Any:
        keys = path.split('.')
        value = self._data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_message(self, key: str, **kwargs) -> str:
        message = self.get(f'messages.{key}', '')

        if not message:
            return f"[Message '{key}' not found]"

        try:
            return message.format(**kwargs)
        except KeyError as e:
            return message

    @property
    def bot_name(self) -> str:
        return self.get('bot.name', 'Music Bot')

    @property
    def bot_version(self) -> str:
        return self.get('bot.version', '1.0.0')

    @property
    def genius_enabled(self) -> bool:
        return self.get('genius.enabled', True) and self.get('features.artist_search', True)

    @property
    def genius_max_songs(self) -> int:
        return self.get('genius.max_songs', 5)

    @property
    def genius_max_description_length(self) -> int:
        return self.get('genius.max_description_length', 600)

    @property
    def albums_per_page(self) -> int:
        return self.get('pagination.albums_per_page', 5)

    @property
    def tracks_per_page(self) -> int:
        return self.get('pagination.tracks_per_page', 8)


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        raise RuntimeError("Config not initialized. Call setup_config() first.")
    return _config


def setup_config(config_path: Path) -> Config:
    global _config
    _config = Config(config_path)
    return _config
