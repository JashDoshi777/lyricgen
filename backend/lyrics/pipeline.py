"""
Lyrics pipeline: LRCLib (synced) -> Genius -> Musixmatch (plain text fallbacks).
"""

from lyrics import lrclib, genius, musixmatch
from recognition.titles import clean_title_artist, strip_featuring, first_artist

NO_LYRICS = {'synced': False, 'lines': [], 'source': 'none'}


def fetch_lyrics(title, artist, album=None, duration=None):
    """
    Args:
        duration: seconds (float) or None. Used to pick the matching version.
    Returns dict {synced, lines:[{time,text}], source, ...}; lines is [] if nothing found.
    """
    title, artist = clean_title_artist(title, artist)
    base_title = strip_featuring(title)
    lead = first_artist(artist)

    attempts = []

    def add(t, a):
        if t and (t, a) not in attempts:
            attempts.append((t, a))

    add(title, artist)
    if artist:
        add(artist, title)          # browser titles may be "Title - Artist": try swapped right away
    add(base_title, artist)
    add(base_title, lead)
    if not artist:
        add(title, '')

    plain = None
    for t, a in attempts:
        res = lrclib.fetch_lyrics(t, a, album, duration)
        if res and res['lines']:
            if res['synced']:
                print(f"[Pipeline] ✓ LRCLib synced: '{t}' / '{a}'")
                return res
            plain = plain or res

    for source in (genius, musixmatch):
        if plain:
            break
        for t, a in attempts[:2]:
            res = source.fetch_lyrics(t, a)
            if res and res['lines']:
                plain = res
                break

    if plain:
        print(f"[Pipeline] ~ plain lyrics only ({plain['source']})")
        return plain

    print(f"[Pipeline] ✗ nothing for '{title}' by '{artist}'")
    return dict(NO_LYRICS)
