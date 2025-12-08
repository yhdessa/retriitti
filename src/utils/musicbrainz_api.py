import aiohttp
import asyncio
from typing import Optional, Dict
from urllib.parse import quote
from utils.logger import get_logger

logger = get_logger(__name__)

USER_AGENT = "TelegramMusicBot/1.0 (https://github.com/yhdessa/retriitti)"

_last_request_time = 0
_rate_limit_delay = 1.0


async def _rate_limit():
    global _last_request_time
    current_time = asyncio.get_event_loop().time()
    time_since_last = current_time - _last_request_time

    if time_since_last < _rate_limit_delay:
        await asyncio.sleep(_rate_limit_delay - time_since_last)

    _last_request_time = asyncio.get_event_loop().time()


async def search_recording(artist: str, title: str, timeout: int = 10) -> Optional[Dict]:
    try:
        await _rate_limit()

        query = f'artist:"{artist}" AND recording:"{title}"'

        url = "https://musicbrainz.org/ws/2/recording/"
        params = {
            'query': query,
            'fmt': 'json',
            'limit': 5
        }
        headers = {
            'User-Agent': USER_AGENT
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    recordings = data.get('recordings', [])

                    if recordings:
                        return recordings[0]
                    else:
                        logger.info(f"No recordings found for: {artist} - {title}")
                        return None

                elif response.status == 503:
                    logger.warning("MusicBrainz API rate limit exceeded")
                    return None
                else:
                    logger.error(f"MusicBrainz API error: {response.status}")
                    return None

    except asyncio.TimeoutError:
        logger.warning(f"Timeout searching MusicBrainz for: {artist} - {title}")
        return None
    except Exception as e:
        logger.error(f"Error searching MusicBrainz: {e}")
        return None


async def fetch_album_name(artist: str, title: str) -> Optional[str]:
    recording = await search_recording(artist, title)

    if recording and recording.get('releases'):
        releases = recording['releases']

        for release in releases:
            release_group = release.get('release-group', {})
            primary_type = release_group.get('primary-type', '')

            if primary_type == 'Album':
                album_name = release.get('title')
                if album_name:
                    logger.info(f"Found album: {album_name} for {artist} - {title}")
                    return album_name

        first_release = releases[0].get('title')
        if first_release:
            logger.info(f"Found release: {first_release} for {artist} - {title}")
            return first_release

    logger.info(f"No album found for: {artist} - {title}")
    return None


async def fetch_full_metadata(artist: str, title: str) -> Dict[str, Optional[str]]:
    recording = await search_recording(artist, title)

    metadata = {
        'album': None,
        'genre': None,
        'year': None,
        'duration': None
    }

    if not recording:
        return metadata

    if recording.get('releases'):
        releases = recording['releases']

        for release in releases:
            release_group = release.get('release-group', {})
            primary_type = release_group.get('primary-type', '')

            if primary_type == 'Album':
                metadata['album'] = release.get('title')

                if release.get('date'):
                    try:
                        metadata['year'] = release['date'].split('-')[0]
                    except:
                        pass
                break

        if not metadata['album'] and releases:
            metadata['album'] = releases[0].get('title')
            if releases[0].get('date'):
                try:
                    metadata['year'] = releases[0]['date'].split('-')[0]
                except:
                    pass

    if recording.get('tags'):
        tags = recording['tags']
        if tags:
            sorted_tags = sorted(tags, key=lambda x: x.get('count', 0), reverse=True)
            if sorted_tags:
                metadata['genre'] = sorted_tags[0].get('name', '').title()

    if recording.get('length'):
        try:
            metadata['duration'] = int(recording['length']) // 1000
        except:
            pass

    logger.info(f"Fetched metadata for {artist} - {title}: {metadata}")
    return metadata


async def enrich_track_metadata(
    artist: str,
    title: str,
    existing_album: Optional[str] = None,
    existing_genre: Optional[str] = None
) -> Dict[str, Optional[str]]:
    if existing_album and existing_genre:
        logger.info(f"Metadata already complete for {artist} - {title}")
        return {
            'album': existing_album,
            'genre': existing_genre
        }

    metadata = await fetch_full_metadata(artist, title)

    return {
        'album': existing_album or metadata.get('album'),
        'genre': existing_genre or metadata.get('genre'),
        'year': metadata.get('year'),
        'duration': metadata.get('duration')
    }


async def fetch_album_from_itunes(artist: str, title: str) -> Optional[str]:
    try:
        url = "https://itunes.apple.com/search"
        params = {
            'term': f"{artist} {title}",
            'media': 'music',
            'entity': 'song',
            'limit': 1
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])

                    if results:
                        album = results[0].get('collectionName')
                        if album:
                            logger.info(f"Found album from iTunes: {album}")
                            return album

        return None

    except Exception as e:
        logger.error(f"Error fetching from iTunes: {e}")
        return None


async def fetch_album_with_fallback(artist: str, title: str) -> Optional[str]:
    album = await fetch_album_name(artist, title)

    if album:
        return album

    logger.info(f"Trying iTunes API as fallback for {artist} - {title}")
    album = await fetch_album_from_itunes(artist, title)

    return album
