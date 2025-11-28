# src/bot.py
import asyncio
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command

# Импортируем наш logger
from utils.logger import setup_logger

# ========== ЗАГРУЗКА КОНФИГУРАЦИИ ==========

BASE_DIR = Path(__file__).parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

# Загружаем YAML конфигурацию
config_path = BASE_DIR / "config.yaml"

try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"Config file not found: {config_path}")
except yaml.YAMLError as e:
    raise ValueError(f"Error parsing YAML config: {e}")

MESSAGES = config["messages"]

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========

log_config = config.get("logging", {})
logger = setup_logger(
    name="music_bot",
    level=log_config.get("level", "INFO"),
    log_to_console=log_config.get("log_to_console", True),
    log_to_file=log_config.get("log_to_file", True),
    file_path=log_config.get("file_path", "logs/bot.log"),
    max_file_size_mb=log_config.get("max_file_size_mb", 10),
    backup_count=log_config.get("backup_count", 5),
    log_format=log_config.get("format", "detailed")
)

logger.info("=" * 60)
logger.info("🤖 Music Finder Bot initialization started")
logger.info(f"📁 Base directory: {BASE_DIR}")
logger.info(f"📄 Config file: {config_path}")
logger.info(f"🔐 Environment file: {env_path}")
logger.info(f"🔑 Bot token loaded: {BOT_TOKEN[:10]}...")
logger.info("=" * 60)

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ========== ОБРАБОТЧИКИ ==========

@router.message(CommandStart())
async def start_handler(message: types.Message):
    """Обработчик коман# src/bot.py"""
import asyncio
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command

# ========== ЗАГРУЗКА КОНФИГУРАЦИИ ==========

# Получаем директорию, где лежит bot.py
BASE_DIR = Path(__file__).parent

# Загружаем переменные окружения из .env
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

# Получаем токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

# Загружаем YAML конфигурацию
config_path = BASE_DIR / "config.yaml"

try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"Config file not found: {config_path}")
except yaml.YAMLError as e:
    raise ValueError(f"Error parsing YAML config: {e}")

MESSAGES = config["messages"]

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ========== ОБРАБОТЧИКИ ==========

@router.message(CommandStart())
async def start_handler(message: types.Message):
    """Обработчик команды /start"""
    text = MESSAGES["start"].format(user=html.bold(message.from_user.full_name))
    await message.answer(text)


@router.message(Command("help"))
async def help_handler(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(MESSAGES["help"])


@router.message(lambda msg: msg.text and msg.text.startswith("/") and " " not in msg.text)
async def unknown_command(message: types.Message):
    """Обработчик неизвестных команд (например /abc)"""
    await message.answer(MESSAGES["unknown_command"])


@router.message()
async def text_handler(message: types.Message):
    """Обработчик текстовых сообщений (поиск музыки)"""
    # Проверяем, что сообщение содержит текст
    if not message.text:
        return

    await message.answer(MESSAGES["processing"])
    await asyncio.sleep(1)

    # TODO: Здесь будет поиск в базе данных
    await message.answer(
        "Demo mode: music search not implemented yet 🎵\n"
        "But your message was:\n\n"
        f"<i>{html.quote(message.text)}</i>"
    )

# ========== ЗАПУСК БОТА ==========

async def main():
    """Основная функция запуска бота"""
    print("=" * 50)
    print("🤖 Music Finder Bot is starting...")
    print(f"📁 Base directory: {BASE_DIR}")
    print(f"📄 Config file: {config_path}")
    print(f"🔐 .env file: {env_path}")
    print(f"🔑 Bot token loaded: {BOT_TOKEN[:10]}...")
    print("=" * 50)

    try:
        # Удаляем webhook (если был установлен)
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook deleted, starting polling...")

        # Запускаем long polling
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Error during polling: {e}")
        raise
    finally:
        await bot.session.close()
        print("\n👋 Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Bot stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
