from aiogram import Router, types, F, html
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils.config import get_config
from utils.logger import get_logger
from db import (
    get_session,
    search_tracks,
    get_track_by_id,
    get_albums_by_artist,
    get_tracks_by_album,
    get_all_artists,
    get_stats
)

logger = get_logger(__name__)
router = Router()

@router.message(Command("stats"))
async def stats_command(message: types.Message):
    config = get_config()

    try:
        async for session in get_session():
            stats = await get_stats(session)

            text = config.get_message(
                'stats.info',
                total_tracks=stats['total_tracks'],
                unique_artists=stats['unique_artists'],
                genres_count=stats['genres_count'],
                last_upload=stats['last_upload']
            )

            if stats.get('unique_albums', 0) > 0:
                text = text.replace(
                    f"👥 Unique artists: {stats['unique_artists']}",
                    f"👥 Unique artists: {stats['unique_artists']}\n💿 Albums: {stats['unique_albums']}"
                )

            await message.answer(text)
            logger.info(f"User {message.from_user.id} requested stats")

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        await message.answer(config.get_message('error'))

@router.message(F.text & ~F.text.startswith('/'))
async def search_handler(message: types.Message):
    config = get_config()
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("❌ Search query is too short. Please enter at least 2 characters.")
        return

    logger.info(f"User {message.from_user.id} searching for: {query}")

    await message.answer(config.get_message('processing'))

    try:
        async for session in get_session():
            albums = await get_albums_by_artist(session, query)

            if albums:
                logger.info(f"Found {len(albums)} albums for artist: {query}")
                await show_albums(message, query, albums, page=0)
                return

            tracks = await search_tracks(
                session=session,
                query=query,
                limit=50
            )

            if not tracks:
                await message.answer(
                    config.get_message('search.no_results', query=html.quote(query))
                )
                logger.info(f"No results for query: {query}")
                return

            artist_tracks = [t for t in tracks if query.lower() in t.artist.lower()]

            if len(artist_tracks) >= 5:
                logger.info(f"Found {len(artist_tracks)} tracks for artist: {query}")
                await show_artist_tracks_no_albums(message, query, artist_tracks[:30])
                return

            if len(tracks) == 1:
                await send_track(message, tracks[0])
                logger.info(f"Sent single track: {tracks[0].track_id}")
                return

            tracks = tracks[:config.get('search.max_results', 5)]
            await show_track_list(message, tracks, query)

    except Exception as e:
        logger.error(f"Error during search: {e}", exc_info=True)
        await message.answer(config.get_message('error'))

def create_track_keyboard(tracks: list, query: str = None) -> InlineKeyboardMarkup:
    buttons = []

    for i, track in enumerate(tracks, 1):
        button_text = f"{i}. {track.title[:30]} - {track.artist[:20]}"
        if len(track.title) > 30:
            button_text = button_text.replace(track.title[:30], track.title[:27] + "...")

        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"track:{track.track_id}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_albums_keyboard(artist: str, albums: list, page: int = 0) -> InlineKeyboardMarkup:
    config = get_config()
    per_page = config.get('pagination.albums_per_page', 5)

    total_pages = (len(albums) - 1) // per_page + 1
    start_idx = page * per_page
    end_idx = start_idx + per_page

    buttons = []

    for album in albums[start_idx:end_idx]:
        buttons.append([
            InlineKeyboardButton(
                text=f"💿 {album[:40]}",
                callback_data=f"album_tracks:{artist}:{album}:0"
            )
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ Prev", callback_data=f"albums:{artist}:{page-1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
    )

    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="Next ▶️", callback_data=f"albums:{artist}:{page+1}")
        )

    if len(nav_buttons) > 1:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_album_tracks_keyboard(artist: str, album: str, tracks: list, page: int = 0) -> InlineKeyboardMarkup:
    config = get_config()
    per_page = config.get('pagination.tracks_per_page', 8)

    total_pages = (len(tracks) - 1) // per_page + 1
    start_idx = page * per_page
    end_idx = start_idx + per_page

    buttons = []

    for i, track in enumerate(tracks[start_idx:end_idx], start_idx + 1):
        buttons.append([
            InlineKeyboardButton(
                text=f"{i}. {track.title[:35]}",
                callback_data=f"track:{track.track_id}"
            )
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"album_tracks:{artist}:{album}:{page-1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
    )

    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"album_tracks:{artist}:{album}:{page+1}")
        )

    if len(nav_buttons) > 1:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="🔙 Back to albums", callback_data=f"back_to_albums:{artist}:0")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("browse"))
async def browse_command(message: types.Message):
    logger.info(f"User {message.from_user.id} requested artist list")

    try:
        async for session in get_session():
            artists = await get_all_artists(session)

            if not artists:
                await message.answer(
                    "📭 <b>Database is empty</b>\n\n"
                    "No artists found in the database yet.\n"
                    "Use /upload to add tracks."
                )
                return

            await show_artists_list(message, artists, page=0)

    except Exception as e:
        logger.error(f"Error in browse command: {e}", exc_info=True)
        await message.answer("❌ Error loading artists list.")


def create_artists_keyboard(artists: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    total_pages = (len(artists) - 1) // per_page + 1
    start_idx = page * per_page
    end_idx = start_idx + per_page

    buttons = []

    for artist in artists[start_idx:end_idx]:
        buttons.append([
            InlineKeyboardButton(
                text=f"🎤 {artist[:40]}",
                callback_data=f"browse_artist:{artist}:0"
            )
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ Prev", callback_data=f"artists_page:{page-1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="noop")
    )

    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="Next ▶️", callback_data=f"artists_page:{page+1}")
        )

    if len(nav_buttons) > 1:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def show_artists_list(message: types.Message, artists: list, page: int = 0):
    text = f"🎤 <b>Artists in Database</b>\n\n"
    text += f"📊 <b>Total artists:</b> {len(artists)}\n\n"
    text += "Select an artist to view their music:"

    keyboard = create_artists_keyboard(artists, page)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("artists_page:"))
async def handle_artists_pagination(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])

    try:
        async for session in get_session():
            artists = await get_all_artists(session)

            if artists:
                text = f"🎤 <b>Artists in Database</b>\n\n"
                text += f"📊 <b>Total artists:</b> {len(artists)}\n\n"
                text += "Select an artist to view their music:"

                keyboard = create_artists_keyboard(artists, page)

                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()
            else:
                await callback.answer("❌ No artists found", show_alert=True)

    except Exception as e:
        logger.error(f"Error handling artists pagination: {e}", exc_info=True)
        await callback.answer("❌ Error loading artists", show_alert=True)


@router.callback_query(F.data.startswith("browse_artist:"))
async def handle_browse_artist(callback: CallbackQuery):
    parts = callback.data.split(":", 2)
    artist = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0

    logger.info(f"User {callback.from_user.id} browsing artist: {artist}")

    try:
        async for session in get_session():
            albums = await get_albums_by_artist(session, artist)

            if albums:
                text = f"🎤 <b>{html.quote(artist)}</b>\n\n"
                text += f"💿 <b>{len(albums)} albums:</b>\n"
                text += "Select an album to view tracks:"

                keyboard = create_albums_keyboard_with_back(artist, albums, page)

                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()
            else:
                tracks = await search_tracks(session, artist, limit=100)

                if tracks:
                    text = f"🎤 <b>{html.quote(artist)}</b>\n\n"
                    text += f"🎵 <b>{len(tracks)} tracks:</b>\n"
                    text += "Select a track to play:"

                    keyboard = create_artist_tracks_keyboard_with_back(tracks, page)

                    await callback.message.edit_text(text, reply_markup=keyboard)
                    await callback.answer()
                else:
                    await callback.answer("❌ No tracks found for this artist", show_alert=True)

    except Exception as e:
        logger.error(f"Error browsing artist: {e}", exc_info=True)
        await callback.answer("❌ Error loading artist", show_alert=True)

def create_albums_keyboard_with_back(artist: str, albums: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    total_pages = (len(albums) - 1) // per_page + 1
    start_idx = page * per_page
    end_idx = start_idx + per_page

    buttons = []

    for album in albums[start_idx:end_idx]:
        buttons.append([
            InlineKeyboardButton(
                text=f"💿 {album[:40]}",
                callback_data=f"album_tracks:{artist}:{album}:0"
            )
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"browse_artist:{artist}:{page-1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
    )

    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"browse_artist:{artist}:{page+1}")
        )

    if len(nav_buttons) > 1:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="🔙 Back to Artists", callback_data="back_to_artists:0")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_artist_tracks_keyboard_with_back(tracks: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    total_pages = (len(tracks) - 1) // per_page + 1
    start_idx = page * per_page
    end_idx = start_idx + per_page

    buttons = []

    for i, track in enumerate(tracks[start_idx:end_idx], start_idx + 1):
        buttons.append([
            InlineKeyboardButton(
                text=f"{i}. {track.title[:35]}",
                callback_data=f"track:{track.track_id}"
            )
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"browse_artist_tracks:{page-1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
    )

    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"browse_artist_tracks:{page+1}")
        )

    if len(nav_buttons) > 1:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="🔙 Back to Artists", callback_data="back_to_artists:0")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("back_to_artists:"))
async def handle_back_to_artists(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])

    try:
        async for session in get_session():
            artists = await get_all_artists(session)

            if artists:
                text = f"🎤 <b>Artists in Database</b>\n\n"
                text += f"📊 <b>Total artists:</b> {len(artists)}\n\n"
                text += "Select an artist to view their music:"

                keyboard = create_artists_keyboard(artists, page)

                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()

    except Exception as e:
        logger.error(f"Error going back to artists: {e}", exc_info=True)
        await callback.answer("❌ Error", show_alert=True)

def create_artist_tracks_keyboard(tracks: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    total_pages = (len(tracks) - 1) // per_page + 1
    start_idx = page * per_page
    end_idx = start_idx + per_page

    buttons = []

    for i, track in enumerate(tracks[start_idx:end_idx], start_idx + 1):
        buttons.append([
            InlineKeyboardButton(
                text=f"{i}. {track.title[:35]}",
                callback_data=f"track:{track.track_id}"
            )
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"artist_tracks_page:{page-1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
    )

    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"artist_tracks_page:{page+1}")
        )

    if len(nav_buttons) > 1:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def show_track_list(message: types.Message, tracks: list, query: str):
    text = f"🎵 <b>Found {len(tracks)} tracks:</b>\n\n"
    text += "Select a track to play:"

    keyboard = create_track_keyboard(tracks, query)
    await message.answer(text, reply_markup=keyboard)


async def show_albums(message: types.Message, artist: str, albums: list, page: int = 0):
    text = f"🎤 <b>{html.quote(artist)}</b>\n\n"
    text += f"💿 <b>Found {len(albums)} albums:</b>\n"
    text += "Select an album to view tracks:"

    keyboard = create_albums_keyboard(artist, albums, page)
    await message.answer(text, reply_markup=keyboard)


async def show_artist_tracks_no_albums(message: types.Message, artist: str, tracks: list, page: int = 0):
    text = f"🎤 <b>{html.quote(artist)}</b>\n\n"
    text += f"🎵 <b>Found {len(tracks)} tracks:</b>\n"
    text += "Select a track to play:"

    keyboard = create_artist_tracks_keyboard(tracks, page)
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("track:"))
async def handle_track_selection(callback: CallbackQuery):
    track_id = int(callback.data.split(":")[1])

    try:
        async for session in get_session():
            track = await get_track_by_id(session, track_id)

            if track:
                await callback.message.edit_reply_markup(reply_markup=None)
                await send_track_callback(callback, track)
                logger.info(f"User {callback.from_user.id} selected track {track_id}")
            else:
                await callback.answer("❌ Track not found", show_alert=True)

    except Exception as e:
        logger.error(f"Error handling track selection: {e}", exc_info=True)
        await callback.answer("❌ Error loading track", show_alert=True)


@router.callback_query(F.data.startswith("albums:"))
async def handle_albums_pagination(callback: CallbackQuery):
    parts = callback.data.split(":")
    artist = parts[1]
    page = int(parts[2])

    try:
        async for session in get_session():
            albums = await get_albums_by_artist(session, artist)

            if albums:
                text = f"🎤 <b>{html.quote(artist)}</b>\n\n"
                text += f"💿 <b>Found {len(albums)} albums:</b>\n"
                text += "Select an album to view tracks:"

                keyboard = create_albums_keyboard(artist, albums, page)

                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()
            else:
                await callback.answer("❌ No albums found", show_alert=True)

    except Exception as e:
        logger.error(f"Error handling albums pagination: {e}", exc_info=True)
        await callback.answer("❌ Error loading albums", show_alert=True)


@router.callback_query(F.data.startswith("album_tracks:"))
async def handle_album_tracks(callback: CallbackQuery):
    parts = callback.data.split(":", 3)
    artist = parts[1]
    album = parts[2]
    page = int(parts[3])

    try:
        async for session in get_session():
            tracks = await get_tracks_by_album(session, artist, album)

            if tracks:
                text = f"💿 <b>{html.quote(album)}</b>\n"
                text += f"👤 <b>{html.quote(artist)}</b>\n\n"
                text += f"🎵 <b>{len(tracks)} tracks:</b>\n"
                text += "Select a track to play:"

                keyboard = create_album_tracks_keyboard(artist, album, tracks, page)

                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()
            else:
                await callback.answer("❌ No tracks in this album", show_alert=True)

    except Exception as e:
        logger.error(f"Error loading album tracks: {e}", exc_info=True)
        await callback.answer("❌ Error loading tracks", show_alert=True)


@router.callback_query(F.data.startswith("back_to_albums:"))
async def handle_back_to_albums(callback: CallbackQuery):
    parts = callback.data.split(":")
    artist = parts[1]
    page = int(parts[2])

    try:
        async for session in get_session():
            albums = await get_albums_by_artist(session, artist)

            if albums:
                text = f"🎤 <b>{html.quote(artist)}</b>\n\n"
                text += f"💿 <b>Found {len(albums)} albums:</b>\n"
                text += "Select an album to view tracks:"

                keyboard = create_albums_keyboard(artist, albums, page)

                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()

    except Exception as e:
        logger.error(f"Error going back to albums: {e}", exc_info=True)
        await callback.answer("❌ Error", show_alert=True)


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery):
    await callback.answer()


async def send_track(message: types.Message, track):
    try:
        caption = f"🎵 <b>{html.quote(track.title)}</b>\n"
        caption += f"👤 <b>Artist:</b> {html.quote(track.artist)}\n"

        if track.album:
            caption += f"💿 <b>Album:</b> {html.quote(track.album)}\n"

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


async def send_track_callback(callback: CallbackQuery, track):
    try:
        caption = f"🎵 <b>{html.quote(track.title)}</b>\n"
        caption += f"👤 <b>Artist:</b> {html.quote(track.artist)}\n"

        if track.album:
            caption += f"💿 <b>Album:</b> {html.quote(track.album)}\n"

        if track.genre:
            caption += f"🎼 <b>Genre:</b> {html.quote(track.genre)}\n"

        if track.duration:
            caption += f"⏱ <b>Duration:</b> {track.duration_formatted()}\n"

        await callback.message.answer_audio(
            audio=track.file_id,
            caption=caption,
            title=track.title,
            performer=track.artist,
            duration=track.duration
        )

        await callback.answer("✅ Track sent!")
        logger.info(f"Track sent: {track.track_id} - {track.title} to user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error sending track {track.track_id}: {e}", exc_info=True)
        await callback.answer("❌ Error sending track", show_alert=True)
