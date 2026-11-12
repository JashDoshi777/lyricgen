"""
Title / artist cleanup shared by detection and the lyrics pipeline.
Strips platform noise ("Official Video", "Remastered", "From \"Movie\"", ...).
"""

import re

_SUFFIX_PATTERNS = [
    r'\s*[\(\[]\s*(Official\s+(Music\s+)?Video|Official\s+Audio|Audio|Lyrics?|Lyric\s+Video|Visualizer|Official\s+Visualizer|Official\s+Live|Live\s+Performance|HD|HQ|4K|MV|M/V)\s*[\)\]]',
    r'\s*[\(\[]\s*(Remaster(ed)?(\s+\d{4})?|\d{4}\s+Remaster(ed)?|Deluxe(\s+Edition)?|Expanded(\s+Edition)?|Anniversary\s+Edition|Bonus\s+Track(\s+Version)?|Super\s+Deluxe|Standard\s+Edition)\s*[\)\]]',
    r'\s*[\(\[]\s*(Amazon\s+Original|Amazon\s+Exclusive)\s*[\)\]]',
    r'\s*[\(\[]\s*From\s+"[^"]*"\s*[\)\]]',
    r'\s*[\(\[]\s*From\s+[^)\]]+[\)\]]',
    r'\s*[\(\[]\s*(Explicit|Clean Version|Radio\s+Edit|Album\s+Version|Original\s+Mix|Single\s+Version)\s*[\)\]]',
    r'\s*-\s*(\d{4}\s+)?Remaster(ed)?(\s+\d{4})?$',
]


def clean_title_artist(title, artist=''):
    """Return (clean_title, clean_artist)."""
    title = title or ''
    artist = artist or ''

    # "Song - Artist | Channel Name": drop the channel part
    title = re.sub(r'\s*[|｜]\s*.*$', '', title).strip() or title

    for pattern in _SUFFIX_PATTERNS:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()

    title = re.sub(r'\s*-\s*(Single|EP)$', '', title, flags=re.IGNORECASE).strip()
    title = re.sub(r'\s*[\-–—|]+\s*$', '', title).strip()

    # "Artist - Title" (YouTube style). Only when we have no artist or it
    # looks like a channel name.
    if ' - ' in title:
        left, right = title.split(' - ', 1)
        if right.strip() and (not artist or re.search(r'VEVO|Topic|Official|Records|Music$', artist, re.I)):
            artist, title = left.strip(), right.strip()

    artist = re.sub(r'VEVO$', '', artist, flags=re.IGNORECASE).strip()
    artist = re.sub(r'\s*-\s*Topic$', '', artist, flags=re.IGNORECASE).strip()
    artist = re.sub(r'\s*(&|and)\s+more\s*$', '', artist, flags=re.IGNORECASE).strip()
    return title.strip(), artist.strip()


def strip_featuring(title):
    return re.sub(r'\s*[\(\[]?\s*(ft\.?|feat\.?|featuring)\s+.*$', '', title, flags=re.IGNORECASE).strip()


def first_artist(artist):
    """'A, B & C' -> 'A' (lyrics DBs match the primary artist best)."""
    return re.split(r'\s*(?:,|&|;|\band\b|\bx\b|feat\.?|ft\.?)\s*', artist or '', maxsplit=1, flags=re.I)[0].strip()
