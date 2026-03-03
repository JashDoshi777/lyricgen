"""
Lyrics pipeline orchestrator.
Fetches lyrics using a multi-source fallback strategy.
Order: LRCLib → Genius → Musixmatch
"""

import re
from lyrics import lrclib, genius, musixmatch


def _clean_for_search(title, artist):
    """
    Clean title/artist for better lyrics API matching.
    Handles metadata from all platforms: YouTube, Spotify, JioSaavn, Amazon Music, etc.
    """
    # Strip all platform-specific suffixes from title
    suffix_patterns = [
        # YouTube-style
        r'\s*[\(\[]\s*(Official\s+(Music\s+)?Video|Official\s+Audio|Audio|Lyrics?|Lyric\s+Video|Visualizer|Official\s+Visualizer|Official\s+Live|Live\s+Performance|HD|HQ|4K|MV|M/V)\s*[\)\]]',
        # Spotify-style edition/remaster tags
        r'\s*[\(\[]\s*(Remastered\s*\d*|Deluxe(\s+Edition)?|Expanded(\s+Edition)?|Anniversary\s+Edition|Bonus\s+Track(\s+Version)?|Super\s+Deluxe|Standard\s+Edition)\s*[\)\]]',
        # Amazon-style
        r'\s*[\(\[]\s*(Amazon\s+Original|Amazon\s+Exclusive)\s*[\)\]]',
        # JioSaavn / Indian platforms — "From "Movie Name""
        r'\s*[\(\[]\s*From\s+"[^"]*"\s*[\)\]]',
        r'\s*[\(\[]\s*From\s+[^)\]]+[\)\]]',
        # General non-essential tags
        r'\s*[\(\[]\s*(Explicit|Clean Version|Radio\s+Edit|Album\s+Version|Original\s+Mix|Single\s+Version)\s*[\)\]]',
    ]

    clean_title = title
    for pattern in suffix_patterns:
        clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE).strip()

    # Remove "- Single", "- EP" suffix (Spotify)
    clean_title = re.sub(r'\s*-\s*(Single|EP)$', '', clean_title, flags=re.IGNORECASE).strip()

    # Remove trailing dashes/pipes left from cleanup
    clean_title = re.sub(r'\s*[\-–—|]+\s*$', '', clean_title).strip()

    # Handle "Artist - Title" format (common from YouTube/browsers)
    if ' - ' in clean_title:
        parts = clean_title.split(' - ', 1)
        if len(parts) == 2 and parts[1].strip():
            artist = parts[0].strip()
            clean_title = parts[1].strip()

    # Clean artist name — strip VEVO, "- Topic", "& More"
    clean_artist = re.sub(r'VEVO$', '', artist, flags=re.IGNORECASE).strip()
    clean_artist = re.sub(r'\s*-\s*Topic$', '', clean_artist, flags=re.IGNORECASE).strip()
    clean_artist = re.sub(r'\s*(&|and)\s+more\s*$', '', clean_artist, flags=re.IGNORECASE).strip()

    # Strip "ft.", "feat." sections from title for cleaner search
    clean_title_search = re.sub(r'\s*(ft\.?|feat\.?)\s+.*$', '', clean_title, flags=re.IGNORECASE).strip()

    return clean_title, clean_artist, clean_title_search


def fetch_lyrics(title, artist, album=None, duration=None):
    """
    Fetch lyrics using the fallback pipeline.

    Args:
        title: Song title.
        artist: Artist name.
        album: Album name (optional).
        duration: Song duration in seconds (optional).

    Returns:
        dict: {synced, lines, raw, source} or default empty result.
    """
    # Clean title/artist for better matching
    clean_title, clean_artist, search_title = _clean_for_search(title, artist)

    if clean_title != title or clean_artist != artist:
        print(f"[Pipeline] Cleaned: '{title}' by '{artist}' → '{clean_title}' by '{clean_artist}'")

    # Source 1: LRCLib (preferred — synced lyrics)
    print(f"[Pipeline] Trying LRCLib for '{clean_title}' by '{clean_artist}'...")
    result = lrclib.fetch_lyrics(clean_title, clean_artist, album, duration)
    if result and result.get('lines'):
        print(f"[Pipeline] ✓ Found lyrics on LRCLib (synced={result['synced']})")
        return result

    # Try LRCLib with search-cleaned title (without "ft." parts)
    if search_title != clean_title:
        result = lrclib.fetch_lyrics(search_title, clean_artist, album, duration)
        if result and result.get('lines'):
            print(f"[Pipeline] ✓ Found lyrics on LRCLib with cleaned search (synced={result['synced']})")
            return result

    # Source 2: Genius (plain text fallback)
    print(f"[Pipeline] Trying Genius...")
    result = genius.fetch_lyrics(clean_title, clean_artist)
    if result and result.get('lines'):
        print(f"[Pipeline] ✓ Found lyrics on Genius")
        return result

    # Source 3: Musixmatch (last resort)
    print(f"[Pipeline] Trying Musixmatch...")
    result = musixmatch.fetch_lyrics(clean_title, clean_artist)
    if result and result.get('lines'):
        print(f"[Pipeline] ✓ Found lyrics on Musixmatch")
        return result

    # Last attempt: try with just the search title (no featuring info)
    if search_title != clean_title:
        print(f"[Pipeline] Retrying with simplified title '{search_title}'...")
        result = musixmatch.fetch_lyrics(search_title, clean_artist)
        if result and result.get('lines'):
            print(f"[Pipeline] ✓ Found lyrics on Musixmatch (simplified)")
            return result

    # No lyrics found
    print(f"[Pipeline] ✗ No lyrics found for '{clean_title}' by '{clean_artist}'")
    return {
        'synced': False,
        'lines': [{'time': 0, 'text': 'No lyrics found for this song.'}],
        'raw': '',
        'source': 'none'
    }
