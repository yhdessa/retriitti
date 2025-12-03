import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command

# Импорты из utils
from utils.logger import setup_logger, get_logger
from utils.genius_api import get_genius_client
from utils.config import setup_config, get_config

# Импорты handlers
from handlers import upload, search

# Импорты из db
from db import init_db, close_db

# ========== ЗАГРУЗКА КОНФИГУРАЦИИ ==========

BASE_DIR = Path(__file__).parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

# Инициализируем конфиг
config_path = BASE_DIR / "config.yaml"
config = setup_config(config_path)

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========

logger = setup_logger(
    name="music_bot",
    level=config.get('logging.level', 'INFO'),
    log_to_console=config.get('logging.log_to_console', True),
    log_to_file=config.get('logging.log_to_file', True),
    file_path=config.get('logging.file_path', 'logs/bot.log'),
    max_file_size_mb=config.get('logging.max_file_size_mb', 10),
    backup_count=config.get('logging.backup_count', 5),
    log_format=config.get('logging.format', 'detailed')
)

logger.info("=" * 60)
logger.info(f"🤖 {config.bot_name} v{config.bot_version} initialization")
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

# Подключаем роутеры из handlers
dp.include_router(upload.router)  # Загрузка треков
dp.include_router(search.router)  # Поиск треков
dp.include_router(router)  # Основные команды

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    admins = config.get('bot.admins', [])
    return user_id in admins

# ========== ОБРАБОТЧИКИ ==========

@router.message(CommandStart())
async def start_handler(message: types.Message):
    """Обработчик команды /start"""
    logger.info(f"User {message.from_user.id} ({message.from_user.full_name}) started bot")
    text = config.get_message('start', user=html.bold(message.from_user.full_name))
    await message.answer(text)


@router.message(Command("help"))
async def help_handler(message: types.Message):
    """Обработчик команды /help"""
    logger.info(f"User {message.from_user.id} requested help")

    # Базовая справка
    text = config.get_message('help')

    # Если администратор — добавляем админские команды
    if is_admin(message.from_user.id):
        text += "\n\n" + config.get_message('help_admin')

    await message.answer(text)


@router.message(Command("about"))
async def about_handler(message: types.Message):
    """Обработчик команды /about"""
    logger.info(f"User {message.from_user.id} requested about")
    text = config.get_message('about', version=config.bot_version)
    await message.answer(text)


@router.message(Command("artist"))
async def artist_handler(message: types.Message):
    """Обработчик команды /artist <имя артиста>"""

    if not config.genius_enabled:
        await message.answer("⚠️ This feature is currently disabled.")
        return

    command_parts = message.text.split(maxsplit=1)

    if len(command_parts) < 2:
        text = config.get_message('artist.usage')
        await message.answer(text)
        return

    artist_name = command_parts[1].strip()
    logger.info(f"User {message.from_user.id} requested artist info: {artist_name}")

    genius = get_genius_client()

    if not genius.is_available():
        text = config.get_message('artist.api_unavailable')
        await message.answer(text)
        logger.error("Genius API not available - check GENIUS_API_TOKEN")
        return

    status_msg = await message.answer(
        config.get_message('artist.searching', artist=html.quote(artist_name))
    )

    try:
        artist_data = genius.search_artist(artist_name)

        if not artist_data:
            text = config.get_message('artist.not_found', artist=html.quote(artist_name))
            await status_msg.edit_text(text)
            logger.warning(f"Artist not found: {artist_name}")
            return

        # Формируем сообщение
        text = f"🎤 <b>{html.quote(artist_data['name'])}</b>\n"

        if config.get('genius.include_alternate_names', True) and artist_data.get('alternate_names'):
            alt_names = ", ".join(artist_data['alternate_names'])
            text += f"<i>Also known as: {html.quote(alt_names)}</i>\n"

        text += "\n"

        if artist_data.get('description'):
            desc = artist_data['description'].strip()
            max_length = config.genius_max_description_length

            if len(desc) > max_length:
                desc_short = desc[:max_length]
                last_period = desc_short.rfind('.')
                if last_period > 0:
                    desc = desc[:last_period + 1]
                else:
                    desc = desc[:max_length - 3] + "..."

            text += f"📖 <b>About:</b>\n{html.quote(desc)}\n\n"

        if config.get('genius.include_stats', True):
            stats_parts = []

            if artist_data.get('followers_count'):
                followers = artist_data['followers_count']
                stats_parts.append(f"👥 {followers:,} followers")

            if artist_data.get('iq'):
                iq = artist_data['iq']
                stats_parts.append(f"🧠 {iq:,} IQ")

            if stats_parts:
                text += " • ".join(stats_parts) + "\n\n"

        if artist_data.get('songs'):
            text += "🔥 <b>Popular songs:</b>\n"
            for i, song in enumerate(artist_data['songs'], 1):
                song_title = html.quote(song['title'])
                song_url = song['url']

                extra_info = ""
                if song.get('release_date'):
                    extra_info = f" ({song['release_date']})"

                text += f"{i}. <a href='{song_url}'>{song_title}</a>{extra_info}\n"
            text += "\n"

        if config.get('genius.include_social_links', True):
            socials = []
            if artist_data.get('instagram'):
                socials.append(f"📸 <a href='https://instagram.com/{artist_data['instagram']}'>Instagram</a>")
            if artist_data.get('twitter'):
                socials.append(f"🐦 <a href='https://twitter.com/{artist_data['twitter']}'>Twitter</a>")
            if artist_data.get('facebook'):
                socials.append(f"👥 <a href='https://facebook.com/{artist_data['facebook']}'>Facebook</a>")

            if socials:
                text += " • ".join(socials) + "\n\n"

        text += f"🔗 <a href='{artist_data['url']}'>View full profile on Genius</a>"

        # Отправка
        if len(text) > 1024:
            if artist_data.get('image_url'):
                await message.answer_photo(photo=artist_data['image_url'])
            await status_msg.edit_text(text, disable_web_page_preview=False)
        else:
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
        text = config.get_message('artist.error')
        await status_msg.edit_text(text)


@router.message(lambda msg: msg.text and msg.text.startswith("/") and " " not in msg.text)
async def unknown_command(message: types.Message):
    """Обработчик неизвестных команд"""
    logger.warning(f"User {message.from_user.id} sent unknown command: {message.text}")
    text = config.get_message('unknown_command')
    await message.answer(text)


# ========== ЗАПУСК БОТА ==========

async def on_startup():
    """Действия при запуске бота"""
    logger.info("==🔧 Initializing database...==")
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("🔧 Closing database connection...")
    try:
        await close_db()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}", exc_info=True)


async def main():
    """Основная функция запуска бота"""
    logger.info("=" * 60)
    logger.info("🚀 Starting bot polling...")
    logger.info("=" * 60)

    try:
        # Инициализация при запуске
        await on_startup()

        # Удаляем webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted")

        # Запускаем polling
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Error during polling: {e}", exc_info=True)
        raise

    finally:
        # Очистка при остановке
        await on_shutdown()
        await bot.session.close()
        logger.info("==👋 Bot stopped==")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️  Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"❌ Critical error: {e}", exc_info=True)
