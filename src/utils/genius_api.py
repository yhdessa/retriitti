import os
import requests
from typing import Optional, Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)


class GeniusClient:

    BASE_URL = "https://api.genius.com"

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("GENIUS_API_TOKEN")

        if not self.api_token:
            logger.warning("GENIUS_API_TOKEN is not set - Genius features will be disabled")
            self.available = False
            return

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "User-Agent": "MusicFinderBot/1.0"
        }
        self.available = True

        logger.info("Genius API client initialized successfully")

    def is_available(self) -> bool:
        return self.available

    def search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        try:
            url = f"{self.BASE_URL}/search"
            params = {"q": query}

            logger.info(f"Searching Genius for: {query}")

            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            hits = data.get("response", {}).get("hits", [])

            logger.info(f"Found {len(hits)} results")
            return hits

        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Genius: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in search: {e}", exc_info=True)
            return None

    def get_artist(self, artist_id: int) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.BASE_URL}/artists/{artist_id}"

            logger.info(f"Fetching artist info for ID: {artist_id}")

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            artist = data.get("response", {}).get("artist", {})

            if not artist:
                logger.warning(f"No artist data for ID: {artist_id}")
                return None

            logger.info(f"Artist info fetched: {artist.get('name')}")
            return artist

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching artist {artist_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_artist: {e}", exc_info=True)
            return None

    def get_artist_songs(
        self,
        artist_id: int,
        sort: str = "popularity",
        per_page: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        try:
            url = f"{self.BASE_URL}/artists/{artist_id}/songs"
            params = {
                "sort": sort,
                "per_page": per_page
            }

            logger.info(f"Fetching songs for artist ID {artist_id}")

            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            songs = data.get("response", {}).get("songs", [])

            logger.info(f"Found {len(songs)} songs")
            return songs

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching songs for artist {artist_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_artist_songs: {e}", exc_info=True)
            return None

    def search_artist(self, artist_name: str) -> Optional[Dict[str, Any]]:
        try:
            hits = self.search(artist_name)
            
            if not hits:
                logger.warning(f"Artist not found: {artist_name}")
                return None

            first_hit = hits[0].get("result", {})
            primary_artist = first_hit.get("primary_artist", {})

            if not primary_artist:
                logger.warning(f"No primary artist in results for: {artist_name}")
                return None

            artist_id = primary_artist.get("id")
            artist_name_found = primary_artist.get("name")

            if not artist_id:
                logger.error("Artist ID not found in search results")
                return None

            logger.info(f"Found artist: {artist_name_found} (ID: {artist_id})")
            artist_full = self.get_artist(artist_id)
            if not artist_full:
                artist_full = primary_artist
            songs = self.get_artist_songs(
                artist_id,
                sort="popularity",
                per_page=5
            )

            result = {
                "name": artist_full.get("name"),
                "id": artist_full.get("id"),
                "url": artist_full.get("url"),
                "image_url": artist_full.get("image_url") or artist_full.get("header_image_url"),
                "description": self._extract_description(artist_full.get("description")),
                "facebook": artist_full.get("facebook_name"),
                "instagram": artist_full.get("instagram_name"),
                "twitter": artist_full.get("twitter_name"),
                "followers_count": artist_full.get("followers_count"),
                "iq": artist_full.get("iq"),
                "alternate_names": artist_full.get("alternate_names", []),
                "songs": []
            }

            if songs:
                for song in songs:
                    result["songs"].append({
                        "title": song.get("title"),
                        "url": song.get("url"),
                        "artist": song.get("primary_artist", {}).get("name"),
                        "pageviews": song.get("stats", {}).get("pageviews"),
                        "release_date": song.get("release_date_for_display")
                    })

            result["song_count"] = len(result["songs"])

            logger.info(f"Successfully fetched artist data for: {result['name']}")
            return result

        except Exception as e:
            logger.error(f"Error in search_artist for '{artist_name}': {e}", exc_info=True)
            return None

    def _extract_description(self, description_data: Any) -> Optional[str]:
        if not description_data:
            return None

        if isinstance(description_data, dict):
            return description_data.get('plain') or description_data.get('html')

        if isinstance(description_data, str):
            return description_data

        return None


_genius_client: Optional[GeniusClient] = None

def get_genius_client() -> GeniusClient:
    global _genius_client

    if _genius_client is None:
        _genius_client = GeniusClient()
    return _genius_client
