"""
Musixmatch lyrics fetcher.
Third fallback source using the unofficial API.
"""

import requests
from lyrics.parser import parse_plain_lyrics


MUSIXMATCH_API = 'https://api.musixmatch.com/ws/1.1'
# Use a community API key (limited, for demo purposes)
# For production, register at https://developer.musixmatch.com/
MUSIXMATCH_API_KEY = '68b101b27747ac13395670e4620b4c29'


def fetch_lyrics(title, artist):
    """
    Fetch lyrics from Musixmatch.

    Args:
        title: Song title.
        artist: Artist name.

    Returns:
        dict or None: {synced: False, lines: [{time, text}], raw: str, source: 'musixmatch'}
    """
    try:
        # Search for the track
        params = {
            'q_track': title,
            'q_artist': artist,
            'apikey': MUSIXMATCH_API_KEY,
            'page_size': 1,
            's_track_rating': 'desc',
            'format': 'json'
        }

        response = requests.get(
            f'{MUSIXMATCH_API}/track.search',
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return None

        data = response.json()
        body = data.get('message', {}).get('body', {})
        # API sometimes returns body as a list (e.g. rate-limited) instead of dict
        if not isinstance(body, dict):
            return None
        tracks = body.get('track_list', [])

        if not tracks:
            return None

        track_id = tracks[0]['track']['track_id']

        # Fetch lyrics using track ID
        lyrics_params = {
            'track_id': track_id,
            'apikey': MUSIXMATCH_API_KEY,
            'format': 'json'
        }

        lyrics_response = requests.get(
            f'{MUSIXMATCH_API}/track.lyrics.get',
            params=lyrics_params,
            timeout=10
        )

        if lyrics_response.status_code != 200:
            return None

        lyrics_data = lyrics_response.json()
        lyrics_body_raw = lyrics_data.get('message', {}).get('body', {})
        if not isinstance(lyrics_body_raw, dict):
            return None
        lyrics_body = lyrics_body_raw.get('lyrics', {})
        lyrics_text = lyrics_body.get('lyrics_body', '')

        if not lyrics_text:
            return None

        # Musixmatch free API truncates lyrics — clean up the notice
        lyrics_text = lyrics_text.split('******* This Lyrics is NOT')[0].strip()
        lyrics_text = lyrics_text.split('...')[0].strip() if lyrics_text.endswith('...') else lyrics_text

        lines = parse_plain_lyrics(lyrics_text)
        return {
            'synced': False,
            'lines': lines,
            'raw': lyrics_text,
            'source': 'musixmatch'
        }

    except Exception as e:
        print(f"[Musixmatch] Error fetching lyrics: {e}")
        return None
