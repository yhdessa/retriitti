from aiogram import Router, types, F, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.config import get_config
from utils.logger import get_logger
from db import get_session, add_track

logger = get_logger(__name__)
router = Router()


class UploadStates(StatesGroup):
    waiting_for_audio = State()


def is_admin(user_id: int) -> bool:
    config = get_config()
    admins = config.get('bot.admins', [])
    return user_id in admins


@router.message(Command("upload"))
async def upload_command(message: types.Message, state: FSMContext):
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
    config = get_config()
    current_state = await state.get_state()

    if current_state is None:
        return

    await state.clear()
    await message.answer(config.get_message('upload.mode_disabled'))
    logger.info(f"User {message.from_user.id} cancelled upload mode")


@router.message(UploadStates.waiting_for_audio, F.audio)
async def handle_audio_upload(message: types.Message, state: FSMContext):
    config = get_config()

    if not is_admin(message.from_user.id):
        await message.answer(config.get_message('upload.not_admin'))
        return

    audio = message.audio

    title = audio.title or audio.file_name or "Unknown Title"
    artist = audio.performer or "Unknown Artist"
    duration = audio.duration
    file_id = audio.file_id
    album = getattr(audio, 'album', None)
    genre = None

    logger.info(f"Received audio: title='{title}', artist='{artist}', album='{album}', file_id='{file_id[:20]}...'")

    try:
        logger.info("Starting database transaction...")

        async for session in get_session():
            logger.info("Session obtained, calling add_track()...")

            track = await add_track(
                session=session,
                title=title,
                artist=artist,
                album=album,
                file_id=file_id,
                genre=genre,
                duration=duration
            )

            logger.info(f"Track created with ID: {track.track_id}")

            duration_str = track.duration_formatted()

            response_text = "✅ <b>Track added to database!</b>\n\n"
            response_text += f"🎵 <b>Title:</b> {html.quote(title)}\n"
            response_text += f"👤 <b>Artist:</b> {html.quote(artist)}\n"

            if album:
                response_text += f"💿 <b>Album:</b> {html.quote(album)}\n"

            if genre:
                response_text += f"🎼 <b>Genre:</b> {html.quote(genre)}\n"

            response_text += f"⏱ <b>Duration:</b> {duration_str}\n"
            response_text += f"🆔 <b>Track ID:</b> {track.track_id}\n\n"
            response_text += "You can continue sending more audio files or send /cancel to exit."

            await message.answer(response_text)

            logger.info(f"Track {track.track_id} saved successfully")

    except Exception as e:
        logger.error(f"❌ Error saving track: {type(e).__name__}: {str(e)}", exc_info=True)

        error_msg = "❌ Error while saving track to database.\n\n"
        error_msg += f"<b>Debug info:</b>\n"
        error_msg += f"Error type: {type(e).__name__}\n"
        error_msg += f"Error: {html.quote(str(e))}"

        await message.answer(error_msg)


@router.message(UploadStates.waiting_for_audio)
async def handle_invalid_upload(message: types.Message):
    config = get_config()
    await message.answer(config.get_message('upload.invalid_audio'))
