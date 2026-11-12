"""Configuration: environment variables / backend/.env"""

import os
import shutil
import sys

from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
# The packaged desktop app points this at a per-user file; from source it's backend/.env
load_dotenv(os.getenv('LIVELYRICS_ENV') or os.path.join(_HERE, '.env'))


def _find_fpcalc():
    explicit = os.getenv('FPCALC_PATH')
    if explicit:
        return explicit
    found = shutil.which('fpcalc')
    if found:
        return found
    for cand in (
        os.path.join(_HERE, '..', 'chromaprint-fpcalc-1.6.0-windows-x86_64', 'fpcalc.exe'),
        '/opt/homebrew/bin/fpcalc', '/usr/local/bin/fpcalc',
    ):
        if os.path.exists(cand):
            return cand
    return ''


class Config:
    HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'live-lyrics-secret-key')

    ACOUSTID_API_KEY = os.getenv('ACOUSTID_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN', '')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')

    # How often the player is polled (seconds)
    POLL_INTERVAL = float(os.getenv('POLL_INTERVAL', 0.5))
    # Audio-fingerprint fallback (only when no player reports metadata)
    FINGERPRINT_INTERVAL = float(os.getenv('FINGERPRINT_INTERVAL', 12))
    FINGERPRINT_DURATION = int(os.getenv('FINGERPRINT_DURATION', 8))
    # Optional: name substring of the loopback input device (macOS: "BlackHole")
    LOOPBACK_DEVICE = os.getenv('LOOPBACK_DEVICE', 'BlackHole')

    FPCALC_PATH = _find_fpcalc()
    DB_PATH = os.getenv('DB_PATH', os.path.join(_HERE, 'data', 'cache.sqlite'))
    FRONTEND_DIST = os.getenv('FRONTEND_DIST', os.path.join(_HERE, '..', 'frontend', 'dist'))
    IS_MAC = sys.platform == 'darwin'
    IS_WINDOWS = sys.platform == 'win32'

    @classmethod
    def validate(cls):
        w = []
        if not cls.GROQ_API_KEY:
            w.append("GROQ_API_KEY not set — AI explanations disabled")
        if not (cls.ACOUSTID_API_KEY and cls.FPCALC_PATH):
            w.append("Fingerprint fallback disabled (needs ACOUSTID_API_KEY + fpcalc) — "
                     "detection relies on the player's now-playing info")
        return w
