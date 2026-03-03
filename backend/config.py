"""
Configuration module for Live Lyrics App.
Loads environment variables and provides app-wide settings.
"""

import os
from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class Config:
    """Application configuration."""

    # ── Server ──────────────────────────────────────
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'live-lyrics-secret-key')

    # ── API Keys ────────────────────────────────────
    ACOUSTID_API_KEY = os.getenv('ACOUSTID_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN', '')

    # ── Detection ───────────────────────────────────
    DETECTION_INTERVAL = int(os.getenv('DETECTION_INTERVAL', 3))
    FINGERPRINT_DURATION = int(os.getenv('FINGERPRINT_DURATION', 5))
    POSITION_POLL_INTERVAL = float(os.getenv('POSITION_POLL_INTERVAL', 0.5))  # 500ms

    # ── ChromaDB Cloud ──────────────────────────────
    CHROMA_API_KEY = os.getenv('CHROMA_API_KEY', '')
    CHROMA_TENANT = os.getenv('CHROMA_TENANT', '')
    CHROMA_DATABASE = os.getenv('CHROMA_DATABASE', '')

    # ── Groq Model ──────────────────────────────────
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

    # ── fpcalc path ─────────────────────────────────
    FPCALC_PATH = os.getenv('FPCALC_PATH', os.path.join(
        os.path.dirname(__file__), '..', 'chromaprint-fpcalc-1.6.0-windows-x86_64', 'fpcalc.exe'
    ))

    @classmethod
    def validate(cls):
        """Log warnings for missing optional keys."""
        warnings = []
        if not cls.ACOUSTID_API_KEY:
            warnings.append("ACOUSTID_API_KEY not set — fingerprint recognition disabled")
        if not cls.GROQ_API_KEY:
            warnings.append("GROQ_API_KEY not set — AI explanations disabled")
        if not cls.GENIUS_ACCESS_TOKEN:
            warnings.append("GENIUS_ACCESS_TOKEN not set — Genius fallback disabled")
        return warnings
