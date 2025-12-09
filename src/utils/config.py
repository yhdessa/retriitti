import os
import yaml
from pathlib import Path
from typing import Any, Optional
from string import Template


class Config:
    def __init__(self, config_data: dict):
        self._data = config_data
        self._cache = {}

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._cache:
            return self._cache[key]

        keys = key.split('.')
        value = self._data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        self._cache[key] = value
        return value

    def get_message(self, key: str, **kwargs) -> str:
        message = self.get(f'messages.{key}')

        if message is None:
            message = self.get(key)

        if message is None:
            return f"[Message '{key}' not found]"

        if not isinstance(message, str):
            return str(message)

        try:
            return message.format(**kwargs)
        except KeyError as e:
            return message
        except Exception as e:
            return message

    @property
    def bot_name(self) -> str:
        """Get bot name"""
        return self.get('bot.name', 'Music Bot')

    @property
    def bot_version(self) -> str:
        return self.get('bot.version', '1.0.0')

    @property
    def genius_enabled(self) -> bool:
        enabled = self.get('genius.enabled', False)
        api_token = os.getenv('GENIUS_API_TOKEN')
        return enabled and bool(api_token)

    @property
    def genius_max_description_length(self) -> int:
        return self.get('genius.max_description_length', 500)

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


def load_env_vars(text: str) -> str:
    import re

    pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

    def replacer(match):
        var_name = match.group(1)
        default_value = match.group(2)

        env_value = os.getenv(var_name)

        if env_value is not None:
            return env_value
        elif default_value is not None:
            return default_value
        else:
            return match.group(0)
    return re.sub(pattern, replacer, text)


def process_config_values(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: process_config_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [process_config_values(item) for item in data]
    elif isinstance(data, str):
        return load_env_vars(data)
    else:
        return data


def setup_config(config_path: Path) -> Config:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        raw_data = yaml.safe_load(f)

    processed_data = process_config_values(raw_data)

    config = Config(processed_data)

    global _global_config
    _global_config = config

    return config


_global_config: Optional[Config] = None


def get_config() -> Config:
    if _global_config is None:
        raise RuntimeError(
            "Config not initialized. Call setup_config() first."
        )
    return _global_config
