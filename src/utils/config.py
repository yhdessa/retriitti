from typing import Any, Dict, Optional
from pathlib import Path
import yaml


class Config:
    """Класс для работы с конфигурацией бота"""

    def __init__(self, config_path: Path):
        """
        Инициализация конфига

        Args:
            config_path: Путь к файлу config.yaml
        """
        self.config_path = config_path
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Загрузить конфигурацию из файла"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML config: {e}")

    def get(self, path: str, default: Any = None) -> Any:
        """
        Получить значение из конфига по пути

        Args:
            path: Путь к значению через точку (например, 'bot.name' или 'genius.max_songs')
            default: Значение по умолчанию, если путь не найден

        Returns:
            Значение из конфига или default

        Examples:
            config.get('bot.name')  # "Music Finder Bot"
            config.get('genius.max_songs')  # 5
            config.get('unknown.path', 'default')  # 'default'
        """
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
        """
        Получить сообщение и отформатировать его

        Args:
            key: Ключ сообщения (например, 'start' или 'artist.usage')
            **kwargs: Параметры для форматирования

        Returns:
            Отформатированное сообщение

        Examples:
            config.get_message('start', user='John')
            config.get_message('artist.searching', artist='The Weeknd')
        """
        message = self.get(f'messages.{key}', '')

        if not message:
            return f"[Message '{key}' not found]"

        try:
            return message.format(**kwargs)
        except KeyError as e:
            return message

    @property
    def bot_name(self) -> str:
        """Имя бота"""
        return self.get('bot.name', 'Music Bot')

    @property
    def bot_version(self) -> str:
        """Версия бота"""
        return self.get('bot.version', '1.0.0')

    @property
    def genius_enabled(self) -> bool:
        """Включён ли Genius API"""
        return self.get('genius.enabled', True) and self.get('features.artist_search', True)

    @property
    def genius_max_songs(self) -> int:
        """Количество песен для загрузки"""
        return self.get('genius.max_songs', 5)

    @property
    def genius_max_description_length(self) -> int:
        """Максимальная длина описания артиста"""
        return self.get('genius.max_description_length', 600)


# Глобальный экземпляр конфига
_config: Optional[Config] = None


def get_config() -> Config:
    """Получить глобальный экземпляр конфига"""
    global _config
    if _config is None:
        raise RuntimeError("Config not initialized. Call setup_config() first.")
    return _config


def setup_config(config_path: Path) -> Config:
    """
    Инициализировать глобальный конфиг

    Args:
        config_path: Путь к config.yaml

    Returns:
        Экземпляр Config
    """
    global _config
    _config = Config(config_path)
    return _config
