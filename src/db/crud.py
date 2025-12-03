from typing import List, Optional
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Track
from utils.logger import get_logger

logger = get_logger(__name__)


async def add_track(
    session: AsyncSession,
    title: str,
    artist: str,
    file_id: str,
    genre: Optional[str] = None,
    duration: Optional[int] = None,
    tags: Optional[str] = None
) -> Track:
    track = Track(
        title=title,
        artist=artist,
        file_id=file_id,
        genre=genre,
        duration=duration,
        tags=tags
    )

    session.add(track)
    await session.flush()
    logger.info(f"Track added: {track.track_id} - {title} by {artist}")
    return track

async def search_tracks(
    session: AsyncSession,
    query: str,
    limit: int = 5
) -> List[Track]:
    search_pattern = f"%{query.lower()}%"

    stmt = select(Track).where(
        (func.lower(Track.title).like(search_pattern)) |
        (func.lower(Track.artist).like(search_pattern))
    ).limit(limit)

    result = await session.execute(stmt)
    tracks = result.scalars().all()

    logger.info(f"Search '{query}' found {len(tracks)} tracks")
    return list(tracks)


async def get_track_by_id(
    session: AsyncSession,
    track_id: int
) -> Optional[Track]:
    """Получить трек по ID"""
    stmt = select(Track).where(Track.track_id == track_id)
    result = await session.execute(stmt)
    track = result.scalar_one_or_none()

    if track:
        logger.info(f"Track found: {track_id} - {track.title}")
    else:
        logger.warning(f"Track not found: {track_id}")

    return track


async def get_track_by_file_id(
    session: AsyncSession,
    file_id: str
) -> Optional[Track]:
    """Получить трек по file_id"""
    stmt = select(Track).where(Track.file_id == file_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_stats(session: AsyncSession) -> dict:
    """Получить статистику по базе данных"""
    # Общее количество треков
    total_tracks_stmt = select(func.count(Track.track_id))
    total_tracks = await session.scalar(total_tracks_stmt)

    # Уникальные артисты
    unique_artists_stmt = select(func.count(distinct(Track.artist)))
    unique_artists = await session.scalar(unique_artists_stmt)

    # Уникальные жанры
    genres_stmt = select(func.count(distinct(Track.genre))).where(Track.genre.isnot(None))
    genres_count = await session.scalar(genres_stmt)

    # Последняя загрузка
    last_upload_stmt = select(func.max(Track.uploaded_at))
    last_upload = await session.scalar(last_upload_stmt)

    return {
        'total_tracks': total_tracks or 0,
        'unique_artists': unique_artists or 0,
        'genres_count': genres_count or 0,
        'last_upload': last_upload.strftime('%Y-%m-%d %H:%M') if last_upload else 'Never'
    }
