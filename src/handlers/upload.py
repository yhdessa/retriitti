from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.config import get_config  # Импортируем функцию
from utils.logger import get_logger
from db import get_session, add_track

logger = get_logger(__name__)
router = Router()

class UploadStates(StatesGroup):
    """Состояния для загрузки треков"""
    waiting_for_audio = State()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    config = get_config()
    admins = config.get('bot.admins', [])
    return user_id in admins


@router.message(Command("upload"))
async def upload_command(message: types.Message, state: FSMContext):
    """Включить режим загрузки треков"""
    config = get_config()

    if not is_admin(message.from_user.id):
        await message.answer(config.get_message('upload.not_admin'))
        logger.warning(f"User {message.from_user.id} tried to upload without permission")
        return

    await state.set_state(UploadStates.waiting_for_audio)
    await message.answer(config.get_message('upload.mode_enabled'))
    logger.info(f"Admin {message.from_user.id} enabled upload mode")


@router.message(Command("cancel"))
async def cancel_upload(message: types.Message, state: FSMContext):
    """Отменить режим загрузки"""
    config = get_config()
    current_state = await state.get_state()

    if current_state is None:
        return

    await state.clear()
    await message.answer(config.get_message('upload.mode_disabled'))
    logger.info(f"User {message.from_user.id} cancelled upload mode")


@router.message(UploadStates.waiting_for_audio, F.audio)
async def handle_audio_upload(message: types.Message, state: FSMContext):
    """Обработка загруженного аудио"""
    config = get_config()

    if not is_admin(message.from_user.id):
        await message.answer(config.get_message('upload.not_admin'))
        return

    audio = message.audio

    title = audio.title or audio.file_name or "Unknown Title"
    artist = audio.performer or "Unknown Artist"
    duration = audio.duration
    file_id = audio.file_id
    genre = None

    logger.info(f"Received audio: {title} by {artist} (file_id: {file_id[:20]}...)")

    try:
        async for session in get_session():
            track = await add_track(
                session=session,
                title=title,
                artist=artist,
                file_id=file_id,
                genre=genre,
                duration=duration
            )

            duration_str = track.duration_formatted()

            await message.answer(
                config.get_message(
                    'upload.success',
                    title=title,
                    artist=artist,
                    genre=genre or "Not specified",
                    duration=duration_str,
                    track_id=track.track_id
                )
            )

            logger.info(f"Track {track.track_id} saved successfully")

    except Exception as e:
        logger.error(f"Error saving track: {e}", exc_info=True)
        await message.answer(config.get_message('upload.error'))


@router.message(UploadStates.waiting_for_audio)
async def handle_invalid_upload(message: types.Message):
    """Обработка неправильного типа файла"""
    config = get_config()
    await message.answer(config.get_message('upload.invalid_audio'))
