from aiogram import Router, types, F
from aiogram.filters import Command
from utils.config import get_config
from utils.logger import get_logger
from utils.musicbrainz_api import fetch_album_with_fallback, enrich_track_metadata
from db import get_session
from db.models import Track
from db.crud import (
    add_track,
    get_track_by_file_id,
    get_tracks_without_album,
    update_track_album,
    count_tracks_without_album
)
from sqlalchemy.exc import IntegrityError

logger = get_logger(__name__)
router = Router()


@router.message(Command("upload"))
async def upload_command(message: types.Message):
    """Handle /upload command - show instructions"""
    config = get_config()
    await message.answer(config.get_message('upload.instruction'))


@router.message(F.audio)
async def handle_audio_upload(message: types.Message):
    """Handle audio file upload with automatic metadata enrichment"""
    config = get_config()
    audio = message.audio

    try:
        # Extract basic metadata from file
        title = audio.title or audio.file_name or "Unknown"
        artist = audio.performer or "Unknown Artist"
        duration = audio.duration

        # Clean up title (remove file extension if present)
        if title.endswith(('.mp3', '.m4a', '.flac', '.wav', '.ogg')):
            title = title.rsplit('.', 1)[0]

        logger.info(f"User {message.from_user.id} uploading: {title} by {artist}")

        # Check for duplicate
        async for session in get_session():
            existing = await get_track_by_file_id(session, audio.file_id)
            if existing:
                logger.warning(f"Duplicate upload attempt: {audio.file_id}")
                await message.answer(
                    "⚠️ <b>Track already exists</b>\n\n"
                    f"This track is already in the database:\n"
                    f"🎵 <b>{existing.title}</b>\n"
                    f"👤 <b>{existing.artist}</b>\n"
                    + (f"💿 <b>{existing.album}</b>\n" if existing.album else "") +
                    f"\n📊 Track ID: {existing.track_id}"
                )
                return

        # Check if we should fetch metadata from internet
        should_fetch = (
            artist != "Unknown Artist"
            and title != "Unknown"
            and title != audio.file_name  # Has proper metadata
            and config.get('metadata.auto_fetch_album', True)  # Feature enabled
        )

        album = None

        if should_fetch:
            # Show searching message
            search_msg = await message.answer(
                "🔍 <b>Searching for album information...</b>\n"
                "⏳ This may take a few seconds..."
            )

            try:
                # Fetch album from MusicBrainz (with iTunes fallback)
                album = await fetch_album_with_fallback(artist, title)

                # Delete search message
                await search_msg.delete()

                if album:
                    logger.info(f"Found album via API: {album}")
                    await message.answer(
                        f"✅ <b>Album found!</b>\n"
                        f"💿 {album}"
                    )
                else:
                    logger.info(f"No album found for {artist} - {title}")
                    await message.answer(
                        "ℹ️ <b>Album not found in databases</b>\n"
                        "Track will be saved without album information."
                    )

            except Exception as e:
                logger.error(f"Error fetching metadata: {e}", exc_info=True)
                await search_msg.delete()
                await message.answer(
                    "⚠️ <b>Could not fetch album info</b>\n"
                    "Saving track with available metadata..."
                )
                album = None
        else:
            if artist == "Unknown Artist" or title == "Unknown":
                logger.info(f"Skipping metadata fetch: incomplete track info")
                await message.answer(
                    "ℹ️ <b>No metadata in file</b>\n"
                    "Please send files with proper artist/title tags for automatic album detection."
                )
            else:
                logger.info(f"Metadata fetch disabled in config")

        # Save to database
        async for session in get_session():
            try:
                track = await add_track(
                    session=session,
                    title=title,
                    artist=artist,
                    file_id=audio.file_id,
                    album=album,
                    genre=None,  # Can be enhanced later
                    duration=duration,
                    tags=None
                )

                await session.commit()

                # Send success message
                success_text = "✅ <b>Track saved successfully!</b>\n\n"
                success_text += f"🎵 <b>Title:</b> {title}\n"
                success_text += f"👤 <b>Artist:</b> {artist}\n"

                if album:
                    success_text += f"💿 <b>Album:</b> {album}\n"

                if duration:
                    minutes = duration // 60
                    seconds = duration % 60
                    success_text += f"⏱ <b>Duration:</b> {minutes}:{seconds:02d}\n"

                success_text += f"\n📊 <b>Track ID:</b> {track.track_id}"

                await message.answer(success_text)
                logger.info(f"Track saved: ID={track.track_id}, Album={album}")

            except IntegrityError as e:
                await session.rollback()
                logger.warning(f"Database integrity error: {e}")
                await message.answer(
                    "⚠️ <b>Could not save track</b>\n\n"
                    "This track may already exist in the database."
                )

            except Exception as e:
                await session.rollback()
                logger.error(f"Database error while saving track: {e}", exc_info=True)
                await message.answer(
                    "❌ <b>Error saving track</b>\n\n"
                    f"Track: {title} by {artist}\n"
                    f"Please try again or contact support."
                )

    except Exception as e:
        logger.error(f"Error processing audio upload: {e}", exc_info=True)
        await message.answer(
            "❌ <b>Error processing track</b>\n\n"
            "Please try again or contact support."
        )


@router.message(F.document)
async def handle_document_audio(message: types.Message):
    """Handle audio files sent as documents"""
    document = message.document

    # Check if it's an audio file
    if document.mime_type and document.mime_type.startswith('audio/'):
        await message.answer(
            "ℹ️ <b>Audio file detected</b>\n\n"
            "Please send audio files as <b>Audio</b> (not as Document) "
            "to preserve metadata.\n\n"
            "📱 <b>In most Telegram clients:</b>\n"
            "1. Select the audio file\n"
            "2. Choose 'Send as Audio' instead of 'Send as File'\n\n"
            "💡 Files with proper metadata work best for automatic album detection!"
        )
        logger.info(f"User {message.from_user.id} sent audio as document: {document.file_name}")


@router.message(Command("bulk_upload"))
async def bulk_upload_command(message: types.Message):
    """Handle bulk upload request"""
    await message.answer(
        "📦 <b>Bulk Upload Guide</b>\n\n"
        "To upload multiple tracks:\n"
        "1️⃣ Select multiple audio files in your file manager\n"
        "2️⃣ Send them all at once to this chat\n"
        "3️⃣ Each file will be processed automatically\n\n"
        "⚠️ <b>Important:</b>\n"
        "• Send files as <b>Audio</b>, not as documents\n"
        "• Files with proper metadata work best\n"
        "• The bot will search for albums automatically\n\n"
        "💡 <b>Tip:</b> Processing multiple files may take time due to API rate limits "
        "(~1 second per track for album lookup)."
    )


@router.message(Command("enrich_all"))
async def enrich_all_command(message: types.Message):
    """Enrich metadata for all tracks missing album info (Admin only)"""

    # Check if user is admin
    user_id = message.from_user.id
    config = get_config()
    admin_ids = config.get('admin_ids', [])

    if user_id not in admin_ids:
        await message.answer(
            "⛔️ <b>Access Denied</b>\n\n"
            "This command is only available to administrators."
        )
        logger.warning(f"Unauthorized /enrich_all attempt by user {user_id}")
        return

    # Check if MusicBrainz is enabled
    if not config.get('musicbrainz.enabled', True):
        await message.answer(
            "❌ <b>MusicBrainz integration is disabled</b>\n\n"
            "Enable it in config.yaml to use this feature."
        )
        return

    status_msg = await message.answer(
        "🔄 <b>Starting metadata enrichment...</b>\n\n"
        "⏳ This may take several minutes depending on the number of tracks."
    )

    try:
        async for session in get_session():
            # Count tracks without album
            total_count = await count_tracks_without_album(session)

            if total_count == 0:
                await status_msg.edit_text(
                    "✅ <b>All tracks already have album information!</b>\n\n"
                    "No enrichment needed."
                )
                return

            # Get tracks without album (limit to 100 at a time)
            limit = min(100, total_count)
            tracks = await get_tracks_without_album(session, limit=limit)

            total = len(tracks)
            updated = 0
            failed = 0
            skipped = 0

            await status_msg.edit_text(
                f"🔄 <b>Processing {total} tracks...</b>\n\n"
                f"📊 Total tracks without album: {total_count}\n"
                f"⚙️ Processing: {total}\n\n"
                f"Progress: 0/{total}"
            )

            logger.info(f"Starting bulk enrichment: {total} tracks")

            for i, track in enumerate(tracks, 1):
                try:
                    # Skip tracks with "Unknown Artist"
                    if track.artist.lower() in ['unknown artist', 'unknown']:
                        skipped += 1
                        continue

                    # Fetch album info
                    album = await fetch_album_with_fallback(track.artist, track.title)

                    if album:
                        # Update track
                        updated_track = await update_track_album(session, track.track_id, album)
                        if updated_track:
                            await session.commit()
                            updated += 1
                            logger.info(f"Enriched track {track.track_id}: {album}")
                        else:
                            failed += 1
                    else:
                        failed += 1
                        logger.info(f"No album found for: {track.artist} - {track.title}")

                    # Update progress every 5 tracks or at the end
                    if i % 5 == 0 or i == total:
                        await status_msg.edit_text(
                            f"🔄 <b>Processing tracks...</b>\n\n"
                            f"Progress: {i}/{total}\n"
                            f"✅ Updated: {updated}\n"
                            f"❌ Not found: {failed}\n"
                            f"⏭ Skipped: {skipped}\n\n"
                            f"⏱ Estimated time: ~{(total - i)} seconds"
                        )

                except Exception as e:
                    logger.error(f"Error enriching track {track.track_id}: {e}", exc_info=True)
                    failed += 1

            # Final report
            success_rate = (updated / total * 100) if total > 0 else 0

            await status_msg.edit_text(
                f"✅ <b>Metadata enrichment complete!</b>\n\n"
                f"📊 <b>Results:</b>\n"
                f"Total processed: {total}\n"
                f"✅ Successfully updated: {updated}\n"
                f"❌ Not found: {failed}\n"
                f"⏭ Skipped: {skipped}\n\n"
                f"📈 Success rate: {success_rate:.1f}%\n\n"
                f"💡 Tracks with updated metadata can now be browsed by album!"
            )

            logger.info(
                f"Enrichment complete: {updated}/{total} updated "
                f"({success_rate:.1f}% success rate)"
            )

    except Exception as e:
        logger.error(f"Error in bulk metadata enrichment: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ <b>Error during metadata enrichment</b>\n\n"
            f"Error: {str(e)[:200]}\n\n"
            "Check logs for more details."
        )


@router.message(Command("album_stats"))
async def album_stats_command(message: types.Message):
    """Show statistics about album coverage"""
    try:
        async for session in get_session():
            from db.crud import get_stats
            stats = await get_stats(session)

            total = stats['total_tracks']
            without_album = stats.get('tracks_without_album', 0)
            with_album = total - without_album

            coverage = (with_album / total * 100) if total > 0 else 0

            text = f"📊 <b>Album Coverage Statistics</b>\n\n"
            text += f"🎵 Total tracks: {total}\n"
            text += f"💿 With album: {with_album}\n"
            text += f"❓ Without album: {without_album}\n\n"
            text += f"📈 Coverage: {coverage:.1f}%\n\n"

            if without_album > 0:
                config = get_config()
                admin_ids = config.get('admin_ids', [])
                if message.from_user.id in admin_ids:
                    text += "💡 Use /enrich_all to automatically fetch missing album info"
                else:
                    text += "💡 Ask an admin to run /enrich_all to fetch missing album info"
            else:
                text += "✅ All tracks have album information!"

            await message.answer(text)

    except Exception as e:
        logger.error(f"Error getting album stats: {e}", exc_info=True)
        await message.answer("❌ Error getting statistics")
