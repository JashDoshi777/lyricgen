"""
Windows System Media Transport Controls (SMTC) reader.
Retrieves currently playing media info from any app using Windows media APIs.
Uses the winrt-Windows.Media.Control package (pre-built wheels, no MSVC needed).
"""

import re
import asyncio
import sys


def _clean_song_info(title, artist):
    """
    Clean metadata from ANY music source so lyrics APIs can match the song.

    Handles:
      - YouTube:    "(Official Music Video)", "VEVO", "Artist - Title" format
      - Spotify:    "(Remastered 2023)", "(Deluxe Edition)", "- Single"
      - JioSaavn:   "(From \"Movie Name\")", Hindi transliteration artifacts
      - Amazon:     "(Amazon Original)", various edition tags
      - General:    "(feat. X)", "(Live)", "(Acoustic)", "(Radio Edit)"

    Returns:
      (clean_title, clean_artist)
    """
    # ── Strip platform-agnostic suffixes from title ──────────
    # YouTube: Official Video, Official Audio, Lyric Video, MV, etc.
    # Spotify: Remastered, Deluxe, Anniversary, Bonus, Single
    # Amazon:  Amazon Original, Amazon Exclusive
    # JioSaavn: From "Movie Name"
    # General: Radio Edit, Acoustic, Live, Demo, Remix tags in parens
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

    # Remove "- Single", "- EP" suffix (Spotify puts this at the end)
    clean_title = re.sub(r'\s*-\s*(Single|EP)$', '', clean_title, flags=re.IGNORECASE).strip()

    # Remove trailing dashes/pipes from cleanup
    clean_title = re.sub(r'\s*[\-–—|]+\s*$', '', clean_title).strip()

    # ── Handle "Artist - Title" format (common for YouTube/browsers) ──
    # Only split on " - " if the artist looks like a channel name
    # (Spotify/Amazon already provide correct artist separately)
    if ' - ' in clean_title:
        parts = clean_title.split(' - ', 1)
        if len(parts) == 2:
            extracted_artist = parts[0].strip()
            extracted_title = parts[1].strip()
            if extracted_title:
                clean_title = extracted_title
                artist = extracted_artist

    # ── Clean artist name ──────────────────────────────────────
    clean_artist = artist
    # YouTube: Remove VEVO suffix
    clean_artist = re.sub(r'VEVO$', '', clean_artist, flags=re.IGNORECASE).strip()
    # YouTube Music: Remove "- Topic" suffix
    clean_artist = re.sub(r'\s*-\s*Topic$', '', clean_artist, flags=re.IGNORECASE).strip()
    # Some platforms append " Music" to artist names
    # JioSaavn: Sometimes adds "Various Artists" or transliteration
    # Remove "& More" or "and more" from artist compilations
    clean_artist = re.sub(r'\s*(&|and)\s+more\s*$', '', clean_artist, flags=re.IGNORECASE).strip()

    return clean_title, clean_artist



async def get_media_info_async():
    """
    Get currently playing media info from Windows SMTC.

    Returns:
        dict or None: {title, artist, album, status} or None if nothing is playing.
    """
    try:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as MediaManager
        )

        # Get the session manager
        manager = await MediaManager.request_async()
        session = manager.get_current_session()

        if session is None:
            return None

        # Get media properties
        info = await session.try_get_media_properties_async()
        playback = session.get_playback_info()

        title = info.title or ''
        artist = info.artist or ''
        album = info.album_title or ''

        if not title:
            return None

        # Clean up YouTube / browser metadata for better lyrics matching
        clean_title, clean_artist = _clean_song_info(title, artist)

        # Map playback status
        status_map = {
            4: 'playing',
            5: 'paused',
            3: 'stopped',
        }
        status = status_map.get(playback.playback_status, 'unknown')

        # Get timeline (position)
        timeline = session.get_timeline_properties()
        position_ms = int(timeline.position.total_seconds() * 1000)

        return {
            'title': clean_title.strip(),
            'artist': clean_artist.strip(),
            'album': album.strip(),
            'status': status,
            'position_ms': position_ms,
            'source': 'smtc'
        }

    except ImportError:
        print("[MediaSession] winrt packages not available — skipping SMTC detection")
        return None
    except Exception as e:
        print(f"[MediaSession] Error reading SMTC: {e}")
        return None


def get_media_info():
    """
    Synchronous wrapper for SMTC media info retrieval.

    Returns:
        dict or None: Media info dict or None.
    """
    if sys.platform != 'win32':
        return None

    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(get_media_info_async())
        loop.close()
        return result
    except Exception as e:
        print(f"[MediaSession] Error: {e}")
        return None
