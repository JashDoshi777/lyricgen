"""
LRCLib lyrics fetcher (primary source for time-synced lyrics).

Alignment depends on picking the lyrics recorded for the *same version* of the
song, so candidates are scored by duration closeness, title/artist similarity,
and whether they are synced.
"""

import re
from difflib import SequenceMatcher

import requests

from lyrics.parser import parse_lrc, parse_plain_lyrics

LRCLIB_API = 'https://lrclib.net/api'
_HEADERS = {'User-Agent': 'LiveLyrics/2.0 (https://github.com/local/livelyrics)'}


def _norm(s):
    return re.sub(r'[^\w\s]', '', (s or '').lower()).strip()


def _sim(a, b):
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


def _score(c, title, artist, duration):
    score = 0.0
    score += _sim(c.get('trackName'), title) * 3
    score += _sim(c.get('artistName'), artist) * 2
    if c.get('syncedLyrics'):
        score += 2
    if duration and c.get('duration'):
        diff = abs(c['duration'] - duration)
        if diff <= 1.5:
            score += 4
        elif diff <= 3:
            score += 2
        elif diff <= 6:
            score += 0
        else:
            score -= min(diff / 4, 6)      # different edit/version -> timestamps won't match
    if c.get('instrumental'):
        score -= 5
    return score


def fetch_lyrics(title, artist, album=None, duration=None):
    """duration is in seconds (float/int) or None."""
    try:
        # 1) Exact signature match (needs duration to be reliable)
        if duration and album:
            r = requests.get(f'{LRCLIB_API}/get', headers=_HEADERS, timeout=8, params={
                'track_name': title, 'artist_name': artist,
                'album_name': album, 'duration': int(round(duration))})
            if r.status_code == 200:
                res = _process(r.json(), duration)
                if res and res['synced']:
                    return res

        # 2) Search, then rank candidates
        candidates = []
        queries = [{'track_name': title, 'artist_name': artist}, {'q': f'{title} {artist}'.strip()}]
        for q in queries:
            r = requests.get(f'{LRCLIB_API}/search', params=q, headers=_HEADERS, timeout=8)
            if r.status_code == 200:
                candidates.extend(r.json() or [])
            if candidates:
                break

        if not candidates:
            return None

        candidates = [c for c in candidates if c.get('syncedLyrics') or c.get('plainLyrics')]
        if not candidates:
            return None
        best = max(candidates, key=lambda c: _score(c, title, artist, duration))
        # Reject clearly wrong matches
        if _sim(best.get('trackName'), title) < 0.5:
            return None
        if artist and _sim(best.get('artistName'), artist) < 0.35:
            return None
        return _process(best, duration)

    except Exception as e:
        print(f"[LRCLib] Error: {e}")
        return None


def _process(data, player_duration=None):
    synced = data.get('syncedLyrics') or ''
    plain = data.get('plainLyrics') or ''
    if synced:
        lines = parse_lrc(synced)
        if lines:
            return {
                'synced': True, 'lines': lines, 'source': 'lrclib',
                'duration': data.get('duration') or 0,
                'match': {'title': data.get('trackName'), 'artist': data.get('artistName')},
            }
    if plain:
        return {'synced': False, 'lines': parse_plain_lyrics(plain), 'source': 'lrclib',
                'duration': data.get('duration') or 0}
    return None
