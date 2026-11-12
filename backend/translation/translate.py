"""
Translation module using MyMemory API.
Translates lyric lines to target language with caching.
"""

import requests
from cache.store import get_cache


MYMEMORY_API = 'https://api.mymemory.translated.net/get'


def translate_text(text, target_lang='en', source_lang='auto'):
    """
    Translate a text string.

    Args:
        text: Text to translate.
        target_lang: Target language code (e.g., 'en', 'es', 'ja').
        source_lang: Source language code (default 'auto').

    Returns:
        str: Translated text.
    """
    if not text or not text.strip():
        return text

    # Check cache first
    cache = get_cache()
    cached = cache.get_translation(text, target_lang)
    if cached:
        return cached

    try:
        lang_pair = f"{'Autodetect' if source_lang == 'auto' else source_lang}|{target_lang}"

        response = requests.get(
            MYMEMORY_API,
            params={
                'q': text,
                'langpair': lang_pair
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            translated = data.get('responseData', {}).get('translatedText', '')

            if translated and translated.lower() != text.lower():
                # Cache the result
                cache.set_translation(text, target_lang, translated)
                return translated

        return text

    except Exception as e:
        print(f"[Translate] Error: {e}")
        return text


def translate_lyrics(lines, target_lang='en', source_lang='auto'):
    """
    Translate a list of lyric lines.

    Args:
        lines: List of {time, text} dicts.
        target_lang: Target language code.
        source_lang: Source language code.

    Returns:
        list: List of {time, text, translation} dicts.
    """
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        texts = list(pool.map(lambda l: translate_text(l['text'], target_lang, source_lang), lines))
    return [{'time': l.get('time'), 'text': l['text'], 'translation': t} for l, t in zip(lines, texts)]


# Supported languages
LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh': 'Chinese',
    'hi': 'Hindi',
    'ar': 'Arabic',
    'ru': 'Russian',
}
