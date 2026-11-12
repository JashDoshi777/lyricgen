"""Cover-art lookup (iTunes Search API: free, no key) + a safe image proxy allowlist."""

import re
from difflib import SequenceMatcher
from urllib.parse import quote, urlparse

import requests

ALLOWED_IMAGE_HOSTS = (
    'mzstatic.com', 'scdn.co', 'ytimg.com', 'ggpht.com', 'googleusercontent.com', 'saavncdn.com',
    'media-amazon.com', 'ssl-images-amazon.com', 'sndcdn.com', 'dzcdn.net', 'tidal.com', 'gaana.com',
)


def _norm(s):
    return re.sub(r'[^\w\s]', '', (s or '').lower()).strip()


def _sim(a, b):
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    return 0.9 if (a in b or b in a) else SequenceMatcher(None, a, b).ratio()


def is_allowed(url):
    try:
        u = urlparse(url)
        return u.scheme == 'https' and any(u.hostname == h or u.hostname.endswith('.' + h) for h in ALLOWED_IMAGE_HOSTS)
    except Exception:
        return False


def proxied(url):
    """URL the frontend should use (same-origin so the canvas can read colours)."""
    return f"/api/art?u={quote(url, safe='')}" if url and is_allowed(url) else (url or '')


def find_artwork(title, artist, album=''):
    """Cover URL for a song; also tries swapped title/artist (browser titles are often 'Song - Artist')."""
    title, artist = (re.split(r'\s*[|｜]', x)[0].strip() for x in (title, artist))
    return _find(title, artist, album) or (_find(artist, title, album) if artist else '')


def _find(title, artist, album=''):
    try:
        r = requests.get('https://itunes.apple.com/search', timeout=6,
                         params={'term': f'{title} {artist}'.strip(), 'media': 'music', 'entity': 'song', 'limit': 8})
        results = r.json().get('results', []) if r.status_code == 200 else []
        best, best_score = None, 0
        for x in results:
            score = _sim(x.get('trackName'), title) * 2 + _sim(x.get('artistName'), artist) \
                + (_sim(x.get('collectionName'), album) * 0.5 if album else 0)
            if score > best_score:
                best, best_score = x, score
        if best and _sim(best.get('trackName'), title) >= 0.6 and (not artist or _sim(best.get('artistName'), artist) >= 0.3):
            return re.sub(r'/\d+x\d+bb', '/600x600bb', best.get('artworkUrl100', ''))
    except Exception as e:
        print(f"[Artwork] {e}")
    return ''


def suggest(query, limit=10):
    """Song suggestions for the search box (iTunes Search API): title, artist, album, cover, length."""
    query = (query or '').strip()
    if len(query) < 2:
        return []
    try:
        r = requests.get('https://itunes.apple.com/search', timeout=6,
                         params={'term': query, 'media': 'music', 'entity': 'song', 'limit': limit})
        out, seen = [], set()
        for x in (r.json().get('results', []) if r.status_code == 200 else []):
            key = (_norm(x.get('trackName')), _norm(x.get('artistName')))
            if key in seen or not x.get('trackName'):
                continue
            seen.add(key)
            art = x.get('artworkUrl100', '')
            out.append({
                'title': x['trackName'],
                'artist': x.get('artistName', ''),
                'album': x.get('collectionName', ''),
                'duration': round((x.get('trackTimeMillis') or 0) / 1000),
                'explicit': x.get('trackExplicitness') == 'explicit',
                'thumb': proxied(re.sub(r'/\d+x\d+bb', '/200x200bb', art)),
                'artwork': re.sub(r'/\d+x\d+bb', '/600x600bb', art),
            })
        return out
    except Exception as e:
        print(f"[Suggest] {e}")
        return []
