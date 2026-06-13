"""
Live Lyrics App — Flask Backend
Main application entry point.
"""

import sys
import os
import time
import threading

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS
from config import Config
from cache.chroma_cache import get_cache
from recognition.detector import SongDetector
from lyrics.pipeline import fetch_lyrics
from groq_explain.explainer import explain_lyric
from translation.translate import translate_lyrics, LANGUAGES
from websocket.events import register_events
from websocket.sync_engine import SyncEngine
from recognition.media_session import get_media_info


# ── App Setup ───────────────────────────────────────

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app, resources={r"/*": {"origins": "*"}})

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False
)

# ── Services ────────────────────────────────────────

cache = get_cache()
detector = SongDetector(socketio=socketio)
sync_engine = SyncEngine(socketio)

# Register WebSocket events
register_events(socketio, detector, cache, sync_engine)


# ── Song Change Handler ─────────────────────────────

def on_song_changed(song_info):
    """Called when the detector finds a new song."""
    title = song_info.get('title', '')
    artist = song_info.get('artist', '')
    album = song_info.get('album', '')

    # Add to history
    cache.add_to_history(title, artist, album)

    # Check lyrics cache
    cached_lyrics = cache.get_lyrics(title, artist)
    if cached_lyrics:
        print(f"[App] Using cached lyrics for '{title}'")
        lyrics_data = cached_lyrics
    else:
        # Fetch lyrics from pipeline
        lyrics_data = fetch_lyrics(title, artist, album)
        if lyrics_data and lyrics_data.get('lines'):
            cache.set_lyrics(title, artist, lyrics_data)

    if lyrics_data and lyrics_data.get('lines'):
        lines = lyrics_data['lines']

        # Get a FRESH SMTC position right now — not the stale one from detection.
        fresh_media = get_media_info()
        if fresh_media and (fresh_media.get('position_ms') or 0) > 0:
            initial_position = fresh_media['position_ms']
        else:
            initial_position = song_info.get('position_ms') or 0

        # SMTC often reports ~14ms for new songs because YouTube/browsers
        # haven't updated their media session yet. But we KNOW:
        #   - Detection interval is 3s (song was playing before we noticed)
        #   - Lyrics fetch took some time too
        # So if SMTC says < 2s, the position is stale—add minimum compensation.
        if initial_position < 2000:
            compensation = int(Config.DETECTION_INTERVAL * 1000) + 2000
            print(f"[App] SMTC position stale ({initial_position}ms < 2s), adding {compensation}ms compensation")
            initial_position += compensation

        print(f"[App] Starting sync: {len(lines)} lines, pos={initial_position}ms")
        sync_engine.start_sync(lines, initial_position)


detector.on_song_changed = on_song_changed

# Re-sync lyrics timing with SMTC position every detection cycle
detector.on_position_update = lambda pos_ms: sync_engine.resync(pos_ms)


def on_status_changed(status, position_ms=0):
    """Called when the detector notices a playback status change (pause/resume)."""
    position_ms = position_ms or 0  # Guard against None
    if status == 'paused':
        print('[App] Song paused — freezing lyrics')
        sync_engine.pause()
    elif status == 'playing':
        print('[App] Song resumed — resuming lyrics')
        sync_engine.resume(position_ms if position_ms > 0 else None)

detector.on_status_changed = on_status_changed


# ── REST API Endpoints ──────────────────────────────

@app.route('/api/status')
def get_status():
    """Get current app status."""
    current = detector.get_current_song()
    return jsonify({
        'running': detector.is_running,
        'current_song': current,
        'position_ms': detector.get_playback_position() if current else 0,
    })


@app.route('/api/lyrics')
def get_lyrics():
    """Get lyrics for the current or specified song."""
    title = request.args.get('title', '')
    artist = request.args.get('artist', '')

    if not title:
        # Use currently playing song
        current = detector.get_current_song()
        if current:
            title = current.get('title', '')
            artist = current.get('artist', '')

    if not title:
        return jsonify({'error': 'No song specified or detected'}), 400

    # Check cache
    cached = cache.get_lyrics(title, artist)
    if cached:
        return jsonify(cached)

    # Fetch from pipeline
    result = fetch_lyrics(title, artist)
    if result and result.get('lines'):
        cache.set_lyrics(title, artist, result)

    return jsonify(result)


@app.route('/api/explain', methods=['POST'])
def get_explanation():
    """Get AI explanation for a lyric line."""
    data = request.json
    lyric_line = data.get('line', '')
    title = data.get('title', '')
    artist = data.get('artist', '')
    context = data.get('context', [])

    if not lyric_line:
        return jsonify({'error': 'No lyric line provided'}), 400

    result = explain_lyric(lyric_line, title, artist, context)
    return jsonify(result)


@app.route('/api/translate', methods=['POST'])
def get_translation():
    """Translate lyrics to target language."""
    data = request.json
    lines = data.get('lines', [])
    target_lang = data.get('target_lang', 'en')
    source_lang = data.get('source_lang', 'auto')

    if not lines:
        return jsonify({'error': 'No lines provided'}), 400

    result = translate_lyrics(lines, target_lang, source_lang)
    return jsonify({'lines': result})


@app.route('/api/languages')
def get_languages():
    """Get supported translation languages."""
    return jsonify(LANGUAGES)


@app.route('/api/history')
def get_history():
    """Get song playback history."""
    limit = request.args.get('limit', 50, type=int)
    history = cache.get_history(limit)
    return jsonify({'history': history})


@app.route('/api/search')
def search_lyrics():
    """Manual song search."""
    title = request.args.get('title', '')
    artist = request.args.get('artist', '')

    if not title:
        return jsonify({'error': 'Title required'}), 400

    result = fetch_lyrics(title, artist)
    if result and result.get('lines'):
        cache.set_lyrics(title, artist, result)

        # Emit as if detected
        socketio.emit('song_detected', {
            'title': title,
            'artist': artist,
            'album': '',
            'source': 'manual',
            'position_ms': 0,
            'timestamp': time.time()
        })

        sync_engine.start_sync(result['lines'], 0)

    return jsonify(result)


# ── Main ────────────────────────────────────────────

if __name__ == '__main__':
    # Validate config
    warnings = Config.validate()
    for w in warnings:
        print(f"⚠ {w}")

    print("\n" + "=" * 50)
    print("  🎵 Live Lyrics App — Backend")
    print("=" * 50)
    print(f"  Server: http://localhost:{Config.PORT}")
    print(f"  WebSocket: ws://localhost:{Config.PORT}")
    print("=" * 50 + "\n")

    # Start song detection
    detector.start()

    # Run the server
    socketio.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )
