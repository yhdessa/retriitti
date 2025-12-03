# src/handlers/search.py

from aiogram import Router, types, F, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.config import get_config  # Импортируем функцию
from utils.logger import get_logger
from db import get_session, search_tracks, get_track_by_id

logger = get_logger(__name__)
router = Router()
class SearchStates(StatesGroup):
    waiting_for_selection = State()


@router.message(Command("stats"))
async def stats_command(message: types.Message):
    """Показать статистику базы данных"""
    config = get_config()

    try:
        from db import get_stats

        async for session in get_session():
            stats = await get_stats(session)

            text = config.get_message(
                'stats.info',
                total_tracks=stats['total_tracks'],
                unique_artists=stats['unique_artists'],
                genres_count=stats['genres_count'],
                last_upload=stats['last_upload']
            )

            await message.answer(text)
            logger.info(f"User {message.from_user.id} requested stats")

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        await message.answer(config.get_message('error'))


@router.message(F.text & ~F.text.startswith('/'))
async def search_handler(message: types.Message, state: FSMContext):
    """Поиск треков по тексту"""
    config = get_config()
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("❌ Search query is too short. Please enter at least 2 characters.")
        return

    logger.info(f"User {message.from_user.id} searching for: {query}")

    await message.answer(config.get_message('processing'))

    try:
        async for session in get_session():
            tracks = await search_tracks(
                session=session,
                query=query,
                limit=config.get('search.max_results', 5)
            )

            if not tracks:
                await message.answer(
                    config.get_message('search.no_results', query=html.quote(query))
                )
                logger.info(f"No results for query: {query}")
                return

            if len(tracks) == 1:
                track = tracks[0]
                await send_track(message, track)
                logger.info(f"Sent single track: {track.track_id}")

            else:
                results_text = ""
                for i, track in enumerate(tracks, 1):
                    duration = track.duration_formatted()
                    results_text += f"{i}. <b>{html.quote(track.title)}</b>\n"
                    results_text += f"   👤 {html.quote(track.artist)}"
                    if track.genre:
                        results_text += f" • 🎼 {html.quote(track.genre)}"
                    results_text += f" • ⏱ {duration}\n\n"

                text = config.get_message(
                    'search.found_multiple',
                    count=len(tracks),
                    results=results_text
                )

                await message.answer(text)
                await state.update_data(tracks=[t.track_id for t in tracks])
                await state.set_state(SearchStates.waiting_for_selection)

                logger.info(f"Showed {len(tracks)} results for query: {query}")

    except Exception as e:
        logger.error(f"Error during search: {e}", exc_info=True)
        await message.answer(config.get_message('error'))


@router.message(SearchStates.waiting_for_selection, F.text.regexp(r'^\d+$'))
async def handle_selection(message: types.Message, state: FSMContext):
    """Обработка выбора трека по номеру"""
    try:
        selection = int(message.text)
        data = await state.get_data()
        track_ids = data.get('tracks', [])

        if selection < 1 or selection > len(track_ids):
            await message.answer(f"❌ Invalid selection. Please choose a number from 1 to {len(track_ids)}")
            return

        track_id = track_ids[selection - 1]

        async for session in get_session():
            track = await get_track_by_id(session, track_id)

            if track:
                await send_track(message, track)
                await state.clear()
                logger.info(f"User {message.from_user.id} selected track {track_id}")
            else:
                await message.answer("❌ Track not found in database.")
                await state.clear()

    except ValueError:
        await message.answer("❌ Please send a number.")
    except Exception as e:
        logger.error(f"Error handling selection: {e}", exc_info=True)
        config = get_config()
        await message.answer(config.get_message('error'))
        await state.clear()


@router.message(SearchStates.waiting_for_selection)
async def handle_invalid_selection(message: types.Message, state: FSMContext):
    """Обработка неправильного выбора"""
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Search cancelled.")
        return

    await state.clear()
    await search_handler(message, state)


async def send_track(message: types.Message, track):
    """Отправить трек пользователю"""
    try:
        caption = f"🎵 <b>{html.quote(track.title)}</b>\n"
        caption += f"👤 <b>Artist:</b> {html.quote(track.artist)}\n"

        if track.genre:
            caption += f"🎼 <b>Genre:</b> {html.quote(track.genre)}\n"

        if track.duration:
            caption += f"⏱ <b>Duration:</b> {track.duration_formatted()}\n"

        await message.answer_audio(
            audio=track.file_id,
            caption=caption,
            title=track.title,
            performer=track.artist,
            duration=track.duration
        )

        logger.info(f"Track sent: {track.track_id} - {track.title} to user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error sending track {track.track_id}: {e}", exc_info=True)
        await message.answer(
            f"❌ Error sending track.\n"
            f"Track ID: {track.track_id}\n"
            f"Title: {html.quote(track.title)}"
        )
