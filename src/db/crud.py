# src/db/crud.py

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
    album: Optional[str] = None,
    genre: Optional[str] = None,
    duration: Optional[int] = None,
    tags: Optional[str] = None
) -> Track:
    """
    Добавить трек в базу данных

    Args:
        session: Сессия БД
        title: Название трека
        artist: Исполнитель
        file_id: Telegram file_id
        album: Альбом
        genre: Жанр
        duration: Длительность в секундах
        tags: Теги через запятую

    Returns:
        Track: Созданный трек
    """
    track = Track(
        title=title,
        artist=artist,
        album=album,
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
    """
    Поиск треков по названию или исполнителю

    Args:
        session: Сессия БД
        query: Поисковый запрос
        limit: Максимальное количество результатов

    Returns:
        List[Track]: Список найденных треков
    """
    search_pattern = f"%{query.lower()}%"

    stmt = select(Track).where(
        (func.lower(Track.title).like(search_pattern)) |
        (func.lower(Track.artist).like(search_pattern)) |
        (func.lower(Track.album).like(search_pattern))
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


async def get_albums_by_artist(
    session: AsyncSession,
    artist: str
) -> List[str]:
    """
    Получить список альбомов артиста

    Args:
        session: Сессия БД
        artist: Имя артиста

    Returns:
        List[str]: Список названий альбомов
    """
    stmt = select(distinct(Track.album)).where(
        func.lower(Track.artist).like(f"%{artist.lower()}%"),
        Track.album.isnot(None)
    ).order_by(Track.album)

    result = await session.execute(stmt)
    albums = [album for album in result.scalars().all() if album]

    logger.info(f"Found {len(albums)} albums for artist: {artist}")
    return albums


async def get_tracks_by_album(
    session: AsyncSession,
    artist: str,
    album: str
) -> List[Track]:
    """
    Получить треки из альбома

    Args:
        session: Сессия БД
        artist: Имя артиста
        album: Название альбома

    Returns:
        List[Track]: Список треков
    """
    stmt = select(Track).where(
        func.lower(Track.artist).like(f"%{artist.lower()}%"),
        Track.album == album
    ).order_by(Track.title)

    result = await session.execute(stmt)
    tracks = result.scalars().all()

    logger.info(f"Found {len(tracks)} tracks in album '{album}' by {artist}")
    return list(tracks)


async def get_all_artists(session: AsyncSession) -> List[str]:
    """
    Получить список всех артистов из БД

    Args:
        session: Сессия БД

    Returns:
        List[str]: Список уникальных артистов, отсортированный по алфавиту
    """
    stmt = select(distinct(Track.artist)).order_by(Track.artist)
    result = await session.execute(stmt)
    artists = result.scalars().all()

    logger.info(f"Found {len(artists)} unique artists in database")
    return list(artists)


async def get_stats(session: AsyncSession) -> dict:
    """Получить статистику по базе данных"""
    total_tracks_stmt = select(func.count(Track.track_id))
    total_tracks = await session.scalar(total_tracks_stmt)

    unique_artists_stmt = select(func.count(distinct(Track.artist)))
    unique_artists = await session.scalar(unique_artists_stmt)

    unique_albums_stmt = select(func.count(distinct(Track.album))).where(Track.album.isnot(None))
    unique_albums = await session.scalar(unique_albums_stmt)

    genres_stmt = select(func.count(distinct(Track.genre))).where(Track.genre.isnot(None))
    genres_count = await session.scalar(genres_stmt)

    last_upload_stmt = select(func.max(Track.uploaded_at))
    last_upload = await session.scalar(last_upload_stmt)

    return {
        'total_tracks': total_tracks or 0,
        'unique_artists': unique_artists or 0,
        'unique_albums': unique_albums or 0,
        'genres_count': genres_count or 0,
        'last_upload': last_upload.strftime('%Y-%m-%d %H:%M') if last_upload else 'Never'
    }
