import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: str = "music_bot",
    level: str = "INFO",
    log_to_console: bool = True,
    log_to_file: bool = True,
    file_path: str = "logs/bot.log",
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    log_format: str = "detailed"
) -> logging.Logger:
    """
    Настраивает и возвращает logger для бота

    Args:
        name: имя логгера
        level: уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_console: выводить логи в консоль
        log_to_file: сохранять логи в файл
        file_path: путь к файлу логов
        max_file_size_mb: максимальный размер файла (МБ)
        backup_count: количество резервных файлов
        log_format: формат логов ("simple" или "detailed")

    Returns:
        Настроенный logger
    """

    # Создаём logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Очищаем существующие handlers (чтобы не дублировать)
    logger.handlers.clear()

    # Форматы логов
    if log_format == "simple":
        formatter = logging.Formatter(
            fmt="%(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:  # detailed
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Handler для консоли (stdout)
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Handler для файла с ротацией
    if log_to_file:
        # Создаём директорию для логов, если её нет
        log_file = Path(file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Ротация: когда файл достигает max_size, создаётся новый
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,  # МБ в байты
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Получить существующий logger

    Args:
        name: имя логгера (если None, возвращает root logger)

    Returns:
        Logger instance
    """
    return logging.getLogger(name or "music_bot")
