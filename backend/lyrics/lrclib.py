"""
LRCLib lyrics fetcher.
Primary source for synchronized (timestamped) lyrics.
API: https://lrclib.net/api
"""

import requests
from lyrics.parser import parse_lrc


LRCLIB_API = 'https://lrclib.net/api'


def fetch_lyrics(title, artist, album=None, duration=None):
    """
    Fetch synchronized lyrics from LRCLib.

    Args:
        title: Song title.
        artist: Artist name.
        album: Album name (optional).
        duration: Song duration in seconds (optional).

    Returns:
        dict or None: {synced: bool, lines: [{time, text}], raw: str, source: 'lrclib'}
    """
    try:
        # Try exact match first
        params = {
            'track_name': title,
            'artist_name': artist,
        }
        if album:
            params['album_name'] = album
        if duration:
            params['duration'] = int(duration)

        response = requests.get(f'{LRCLIB_API}/get', params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return _process_response(data)

        # Fallback: search
        search_params = {'q': f'{title} {artist}'}
        response = requests.get(f'{LRCLIB_API}/search', params=search_params, timeout=10)

        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0:
                return _process_response(results[0])

        return None

    except Exception as e:
        print(f"[LRCLib] Error fetching lyrics: {e}")
        return None


def _process_response(data):
    """Process a LRCLib API response into structured format."""
    synced_lyrics = data.get('syncedLyrics', '')
    plain_lyrics = data.get('plainLyrics', '')

    if synced_lyrics:
        lines = parse_lrc(synced_lyrics)
        return {
            'synced': True,
            'lines': lines,
            'raw': synced_lyrics,
            'source': 'lrclib',
            'duration': data.get('duration', 0)
        }
    elif plain_lyrics:
        from lyrics.parser import parse_plain_lyrics
        lines = parse_plain_lyrics(plain_lyrics)
        return {
            'synced': False,
            'lines': lines,
            'raw': plain_lyrics,
            'source': 'lrclib'
        }

    return None
