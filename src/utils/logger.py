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

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    logger.handlers.clear()

    if log_format == "simple":
        formatter = logging.Formatter(
            fmt="%(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_to_file:
        log_file = Path(file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if not log_file.exists():
            log_file.touch()
            log_file.chmod(0o666)

        try:
            file_handler = RotatingFileHandler(
                filename=str(log_file),
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            logger.debug(f"Log file initialized: {log_file.absolute()}")

        except PermissionError as e:
            logger.error(f"Cannot write to log file {log_file}: {e}")
            logger.warning("Logging to file disabled, using console only")

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "music_bot")
