"""
Genius lyrics fetcher.
Fallback source for plain-text lyrics (scraping).
"""

import re
import requests
from bs4 import BeautifulSoup
from config import Config
from lyrics.parser import parse_plain_lyrics


GENIUS_API = 'https://api.genius.com'


def fetch_lyrics(title, artist):
    """
    Fetch lyrics from Genius (search + scrape).

    Args:
        title: Song title.
        artist: Artist name.

    Returns:
        dict or None: {synced: False, lines: [{time, text}], raw: str, source: 'genius'}
    """
    token = Config.GENIUS_ACCESS_TOKEN
    if not token:
        return None

    try:
        # Search for the song
        headers = {'Authorization': f'Bearer {token}'}
        params = {'q': f'{title} {artist}'}
        response = requests.get(
            f'{GENIUS_API}/search',
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return None

        data = response.json()
        hits = data.get('response', {}).get('hits', [])

        if not hits:
            return None

        # Get the first result's URL
        song_url = hits[0]['result']['url']

        # Scrape lyrics from the page
        lyrics_text = _scrape_lyrics(song_url)
        if not lyrics_text:
            return None

        lines = parse_plain_lyrics(lyrics_text)
        return {
            'synced': False,
            'lines': lines,
            'raw': lyrics_text,
            'source': 'genius'
        }

    except Exception as e:
        print(f"[Genius] Error fetching lyrics: {e}")
        return None


def _scrape_lyrics(url):
    """
    Scrape lyrics text from a Genius song page.

    Args:
        url: Genius song page URL.

    Returns:
        str: Lyrics text or empty string.
    """
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Genius uses divs with data-lyrics-container attribute
        containers = soup.find_all('div', {'data-lyrics-container': 'true'})

        if not containers:
            return ''

        lyrics_parts = []
        for container in containers:
            # Replace <br> with newlines
            for br in container.find_all('br'):
                br.replace_with('\n')
            text = container.get_text()
            lyrics_parts.append(text)

        lyrics = '\n'.join(lyrics_parts)

        # Clean up: remove section headers like [Verse 1]
        lyrics = re.sub(r'\[.*?\]', '', lyrics)
        # Remove excessive blank lines
        lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)

        return lyrics.strip()

    except Exception as e:
        print(f"[Genius] Error scraping: {e}")
        return ''
