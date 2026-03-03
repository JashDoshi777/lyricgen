"""
Audio fingerprint recognition using Chromaprint + AcoustID.
Identifies songs from captured audio data.
"""

import os
import subprocess
import tempfile
import requests
from config import Config


ACOUSTID_API_URL = 'https://api.acoustid.org/v2/lookup'


def generate_fingerprint(wav_data):
    """
    Generate a Chromaprint fingerprint from WAV audio data.

    Args:
        wav_data: WAV file bytes.

    Returns:
        tuple: (duration, fingerprint_string) or (None, None) on failure.
    """
    fpcalc_path = Config.FPCALC_PATH

    if not os.path.exists(fpcalc_path):
        print(f"[Fingerprint] fpcalc not found at {fpcalc_path}")
        return None, None

    try:
        # Write WAV data to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(wav_data)
            tmp_path = tmp.name

        # Run fpcalc
        result = subprocess.run(
            [fpcalc_path, '-raw', '-json', tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        os.unlink(tmp_path)

        if result.returncode != 0:
            print(f"[Fingerprint] fpcalc error: {result.stderr}")
            return None, None

        import json
        data = json.loads(result.stdout)
        duration = data.get('duration', 0)
        fingerprint = data.get('fingerprint', '')

        return duration, fingerprint

    except Exception as e:
        print(f"[Fingerprint] Error generating fingerprint: {e}")
        return None, None


def lookup_acoustid(duration, fingerprint):
    """
    Look up a fingerprint against the AcoustID database.

    Args:
        duration: Audio duration in seconds.
        fingerprint: Chromaprint fingerprint string.

    Returns:
        dict or None: {title, artist, album} or None if no match.
    """
    api_key = Config.ACOUSTID_API_KEY
    if not api_key:
        print("[Fingerprint] AcoustID API key not configured")
        return None

    try:
        params = {
            'client': api_key,
            'duration': int(duration),
            'fingerprint': fingerprint,
            'meta': 'recordings releasegroups',
            'format': 'json'
        }

        response = requests.get(ACOUSTID_API_URL, params=params, timeout=10)
        data = response.json()

        if data.get('status') != 'ok' or not data.get('results'):
            return None

        # Get the best match
        best = data['results'][0]
        if best.get('score', 0) < 0.5:
            return None

        recordings = best.get('recordings', [])
        if not recordings:
            return None

        recording = recordings[0]
        title = recording.get('title', '')
        artists = recording.get('artists', [])
        artist = artists[0]['name'] if artists else ''

        # Try to get album
        album = ''
        release_groups = recording.get('releasegroups', [])
        if release_groups:
            album = release_groups[0].get('title', '')

        return {
            'title': title,
            'artist': artist,
            'album': album,
            'source': 'acoustid',
            'score': best.get('score', 0)
        }

    except Exception as e:
        print(f"[Fingerprint] AcoustID lookup error: {e}")
        return None


def identify_from_audio(wav_data):
    """
    Full pipeline: WAV data → fingerprint → AcoustID lookup → song info.

    Args:
        wav_data: WAV file bytes.

    Returns:
        dict or None: Song metadata or None.
    """
    duration, fingerprint = generate_fingerprint(wav_data)
    if not fingerprint:
        return None

    return lookup_acoustid(duration, fingerprint)
