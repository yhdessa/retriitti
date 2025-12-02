# src/bot.py
import asyncio
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command

from utils.logger import setup_logger, get_logger
from utils.genius_api import get_genius_client

# ========== ЗАГРУЗКА КОНФИГУРАЦИИ ==========

BASE_DIR = Path(__file__).parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

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
    """Обработчик команды /start"""
    logger.info(f"User {message.from_user.id} ({message.from_user.full_name}) started bot")
    text = MESSAGES["start"].format(user=html.bold(message.from_user.full_name))
    await message.answer(text)


@router.message(Command("help"))
async def help_handler(message: types.Message):
    """Обработчик команды /help"""
    logger.info(f"User {message.from_user.id} requested help")
    help_text = MESSAGES["help"] + "\n\n" + \
                "<b>Additional commands:</b>\n" + \
                "/artist &lt;name&gt; — get artist info from Genius"
    await message.answer(help_text)


@router.message(Command("artist"))
async def artist_handler(message: types.Message):
    """Обработчик команды /artist <имя артиста>"""
    command_parts = message.text.split(maxsplit=1)

    if len(command_parts) < 2:
        await message.answer(
            "ℹ️ <b>Usage:</b>\n"
            "/artist <b>&lt;artist name&gt;</b>\n\n"
            "<b>Examples:</b>\n"
            "/artist The Weeknd\n"
            "/artist My Bloody Valentine\n"
            "/artist Radiohead"
        )
        return

    artist_name = command_parts[1].strip()
    logger.info(f"User {message.from_user.id} requested artist info: {artist_name}")

    genius = get_genius_client()

    if not genius.is_available():
        await message.answer(
            "⚠️ <b>Genius API is currently unavailable</b>\n\n"
            "Artist search feature is temporarily disabled.\n"
            "Please contact the administrator."
        )
        logger.error("Genius API not available - check GENIUS_API_TOKEN")
        return

    status_msg = await message.answer(
        f"🔍 Searching for <b>{html.quote(artist_name)}</b> on Genius..."
    )

    try:
        artist_data = genius.search_artist(artist_name)

        if not artist_data:
            await status_msg.edit_text(
                f"❌ Artist <b>{html.quote(artist_name)}</b> not found on Genius.\n\n"
                "Try a different spelling or check the artist name."
            )
            logger.warning(f"Artist not found: {artist_name}")
            return

        text = f"🎤 <b>{html.quote(artist_data['name'])}</b>\n\n"

        if artist_data.get('description'):
            desc = artist_data['description']
            if len(desc) > 200:
                desc = desc[:197] + "..."
            text += f"📝 {html.quote(desc)}\n\n"

        if artist_data.get('followers_count'):
            followers = artist_data['followers_count']
            text += f"👥 <b>Followers:</b> {followers:,}\n\n"

        if artist_data.get('songs'):
            text += "🔥 <b>Popular songs:</b>\n"
            for i, song in enumerate(artist_data['songs'], 1):
                song_title = html.quote(song['title'])
                song_url = song['url']
                text += f"{i}. <a href='{song_url}'>{song_title}</a>\n"
            text += "\n"

        socials = []
        if artist_data.get('instagram'):
            socials.append(f"📸 <a href='https://instagram.com/{artist_data['instagram']}'>Instagram</a>")
        if artist_data.get('twitter'):
            socials.append(f"🐦 <a href='https://twitter.com/{artist_data['twitter']}'>Twitter</a>")
        if artist_data.get('facebook'):
            socials.append(f"👥 <a href='https://facebook.com/{artist_data['facebook']}'>Facebook</a>")

        if socials:
            text += " • ".join(socials) + "\n\n"

        text += f"🔗 <a href='{artist_data['url']}'>View on Genius</a>"

        if artist_data.get('image_url'):
            try:
                await message.answer_photo(
                    photo=artist_data['image_url'],
                    caption=text
                )
                await status_msg.delete()
            except Exception as e:
                logger.warning(f"Failed to send photo: {e}")
                await status_msg.edit_text(text)
        else:
            await status_msg.edit_text(text)

        logger.info(f"Artist info sent successfully: {artist_data['name']}")

    except Exception as e:
        logger.error(f"Error in artist_handler: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ An error occurred while fetching artist info.\n"
            "Please try again later."
        )


@router.message(lambda msg: msg.text and msg.text.startswith("/") and " " not in msg.text)
async def unknown_command(message: types.Message):
    """Обработчик неизвестных команд"""
    logger.warning(f"User {message.from_user.id} sent unknown command: {message.text}")
    await message.answer(MESSAGES["unknown_command"])


@router.message()
async def text_handler(message: types.Message):
    """Обработчик текстовых сообщений (поиск музыки)"""
    if not message.text:
        return

    logger.info(f"User {message.from_user.id} searched for: {message.text}")

    await message.answer(MESSAGES["processing"])
    await asyncio.sleep(1)

    await message.answer(
        "🎵 <b>Demo mode</b>\n\n"
        "Music search not implemented yet.\n"
        "Your search query:\n\n"
        f"<i>{html.quote(message.text)}</i>\n\n"
        "Coming soon: database integration! 🚀\n\n"
        "Try /artist &lt;name&gt; to search for artist info!"
    )


# ========== ЗАПУСК БОТА ==========

async def main():
    """Основная функция запуска бота"""
    logger.info("=" * 60)
    logger.info("🚀 Starting bot polling...")
    logger.info("=" * 60)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted")

        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Error during polling: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()
        logger.info("👋 Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️  Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"❌ Critical error: {e}", exc_info=True)
