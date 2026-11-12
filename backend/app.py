"""
LiveLyrics backend — Flask + Socket.IO.
Serves the API, the realtime stream, and (if built) the web UI at http://localhost:5000
"""

import multiprocessing
multiprocessing.freeze_support()   # required in the packaged app: stops Python re-launching the whole server

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from config import Config
from cache.store import get_cache
from core.tracker import Tracker
from lyrics.pipeline import fetch_lyrics
from groq_explain.explainer import explain_lyric
from lyrics.artwork import is_allowed, suggest, find_artwork, proxied
from cache.store import song_key
from translation.translate import translate_lyrics, LANGUAGES

DIST = os.path.abspath(Config.FRONTEND_DIST)

app = Flask(__name__, static_folder=None)
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app, resources={r'/api/*': {'origins': '*'}})
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

cache = get_cache()
tracker = Tracker(socketio, cache)


# ── Realtime ────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    snap = tracker.snapshot()
    if snap['song']:
        emit('song', snap['song'])
        emit('lyrics', snap['lyrics'])
    emit('playback', snap['playback'])


@socketio.on('request_state')
def on_request_state():
    on_connect()


# ── REST ────────────────────────────────────────────

@app.get('/api/status')
def status():
    snap = tracker.snapshot()
    return jsonify({**snap, 'platform': sys.platform,
                    'groq': bool(Config.GROQ_API_KEY),
                    'fingerprint': bool(Config.ACOUSTID_API_KEY and Config.FPCALC_PATH)})


@app.post('/api/explain')
def explain():
    d = request.get_json(silent=True) or {}
    if not d.get('line'):
        return jsonify({'error': 'No lyric line provided'}), 400
    return jsonify(explain_lyric(d['line'], d.get('title', ''), d.get('artist', ''), d.get('context', [])))


@app.post('/api/translate')
def translate():
    d = request.get_json(silent=True) or {}
    lines = d.get('lines', [])
    if not lines:
        return jsonify({'error': 'No lines provided'}), 400
    return jsonify({'lines': translate_lyrics(lines, d.get('target_lang', 'en'), d.get('source_lang', 'auto'))})


@app.get('/api/languages')
def languages():
    return jsonify(LANGUAGES)


@app.get('/api/history')
def history():
    items = cache.get_history(request.args.get('limit', 50, type=int))
    missing = [h for h in items if not h['artwork']]
    if missing:
        _fill_covers(missing)
    return jsonify({'history': items})


def _fill_covers(items):
    """Backfill covers for songs played before we had one (cached; misses are remembered)."""
    from concurrent.futures import ThreadPoolExecutor

    def fill(h):
        key = 'art|' + song_key(h['title'], h['artist'])
        if cache._get('artmiss', key):
            return
        url = cache._get('art', key) or find_artwork(h['title'], h['artist'])
        if not url:
            cache._set('artmiss', key, 1)
            return
        cache._set('art', key, url)
        h['artwork'] = proxied(url)
        cache.set_history_artwork(h['title'], h['artist'], h['artwork'])

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(fill, items))


@app.delete('/api/history')
def clear_history():
    cache.clear_history()
    return jsonify({'ok': True})


@app.post('/api/seek')
def seek():
    """Manual sync: 'the line at this timestamp is being sung right now'."""
    d = request.get_json(silent=True) or {}
    return jsonify({'ok': tracker.control('seek', float(d.get('position_sec', 0)))})


@app.post('/api/control')
def control():
    d = request.get_json(silent=True) or {}
    return jsonify({'ok': bool(tracker.control(d.get('action', '')))})


@app.post('/api/offset')
def offset():
    d = request.get_json(silent=True) or {}
    tracker.set_offset(int(d.get('offset_ms', 0)))
    return jsonify({'ok': True})


@app.post('/api/live')
def live():
    """Back to whatever the player is playing right now."""
    return jsonify({'ok': tracker.resume_live()})


@app.get('/api/suggest')
def suggest_songs():
    return jsonify({'results': suggest(request.args.get('q', ''))})


@app.get('/api/search')
def search():
    title = request.args.get('title', '').strip()
    artist = request.args.get('artist', '').strip()
    if not title:
        return jsonify({'error': 'Title required'}), 400
    tracker.play_manual(title, artist, request.args.get('album', ''),
                        request.args.get('artwork', ''), request.args.get('duration', 0, type=float))
    return jsonify({'ok': True})


@app.get('/api/art')
def art():
    """Same-origin proxy for cover images (lets the UI sample colours from them)."""
    import requests
    from flask import Response
    url = request.args.get('u', '')
    if not is_allowed(url):
        return ('', 400)
    cached = _art_cache.get(url)
    if cached is None:
        try:
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                return ('', 404)
            cached = (r.content, r.headers.get('Content-Type', 'image/jpeg'))
            if len(_art_cache) > 200:
                _art_cache.clear()
            _art_cache[url] = cached
        except Exception:
            return ('', 502)
    return Response(cached[0], mimetype=cached[1], headers={'Cache-Control': 'public, max-age=86400'})


_art_cache = {}


_widget_proc = None


@app.post('/api/widget/launch')
def launch_widget():
    """Start the Electron desktop widget (local machine only)."""
    import subprocess
    global _widget_proc
    if request.remote_addr not in ('127.0.0.1', '::1'):
        return jsonify({'ok': False, 'message': 'Only available on this computer.'}), 403
    if _widget_proc and _widget_proc.poll() is None:
        return jsonify({'ok': True, 'message': 'Desktop widget is already running.'})
    edir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'electron'))
    if not os.path.isdir(os.path.join(edir, 'node_modules')):
        return jsonify({'ok': False, 'message': 'Run `npm install` in the electron folder first.'})
    env = {k: v for k, v in os.environ.items() if k != 'ELECTRON_RUN_AS_NODE'}
    env['LYRICS_PORT'] = str(Config.PORT)
    try:
        _widget_proc = subprocess.Popen(['node', 'launch.js'], cwd=edir, env=env, start_new_session=True,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        return jsonify({'ok': False, 'message': 'Node.js not found on PATH.'})
    return jsonify({'ok': True, 'message': 'Desktop widget opening…'})


# ── Web UI (production build) ───────────────────────

@app.get('/', defaults={'path': ''})
@app.get('/<path:path>')
def web(path):
    if os.path.isdir(DIST):
        full = os.path.join(DIST, path)
        if path and os.path.isfile(full):
            return send_from_directory(DIST, path)
        return send_from_directory(DIST, 'index.html')
    return ('<h3>LiveLyrics backend is running.</h3><p>Build the UI with '
            '<code>cd frontend && npm run build</code>, or run <code>npm run dev</code> '
            'and open http://localhost:5173.</p>'), 200


if __name__ == '__main__':
    for w in Config.validate():
        print(f"⚠ {w}")
    print(f"\n  🎵 LiveLyrics  →  http://localhost:{Config.PORT}\n")
    tracker.start()
    socketio.run(app, host=Config.HOST, port=Config.PORT, debug=False,
                 use_reloader=False, allow_unsafe_werkzeug=True)
