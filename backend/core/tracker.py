"""
Tracker — detects what is playing and owns the ONE playback clock.

Why alignment is now solid:
  * The player (Spotify / Music / SMTC / browser) is the only source of truth.
  * We keep a single clock: position = anchor_pos + (now - anchor_time) while playing.
  * Each poll nudges the clock gently (small drift) or snaps it (seek / restart),
    and ignores stale/identical readings.
  * Clients just interpolate from the last `playback` message — no speed warping,
    no guessed "compensation" constants.
  * Lyrics are matched by song duration, so timestamps belong to the same version.
  * A per-song user offset (ms) is stored and sent with the song.
"""

import threading
import time
import uuid

from config import Config
from recognition.media_session import get_media_info, control
from recognition.fingerprint import identify_from_audio
from audio_capture.capture import capture_system_audio, check_audio_level
from lyrics.pipeline import fetch_lyrics
from cache.store import song_key
from lyrics.artwork import find_artwork, proxied

SNAP_THRESHOLD = 1.0      # s: beyond this, treat as a seek
NUDGE_THRESHOLD = 0.12    # s: below this, ignore jitter
NUDGE_GAIN = 0.4
COARSE_TICK_BIAS = 0.15  # s: whole-second timers: a new second was seen ~half a poll after it began
COARSE_GAIN = 0.2         # slower averaging for those noisy readings
HEARTBEAT = 2.0           # s: re-broadcast playback so clients self-heal
IDLE_AFTER = 4.0          # s without any media info -> consider playback stopped


class Tracker:
    def __init__(self, socketio, cache):
        self.sio = socketio
        self.cache = cache
        self._lock = threading.RLock()
        self._running = False

        self.song = None            # dict (see _new_song)
        self.lyrics = None          # dict {song_id, status, lines, synced, source}
        self._key = None
        self._player_key = None

        # clock
        self._anchor_pos = 0.0
        self._anchor_time = time.monotonic()
        self.playing = False
        self.position_known = True
        self._last_reading = None
        self._last_beat = 0.0
        self._last_seen = 0.0
        self._last_fp = 0.0
        self._fp_busy = False
        self._coarse = False

    # ───────────── public ─────────────

    def start(self):
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._loop, daemon=True, name='tracker').start()

    def stop(self):
        self._running = False

    def position(self):
        with self._lock:
            return self._pos_unlocked()

    def snapshot(self):
        with self._lock:
            return {
                'song': self.song,
                'lyrics': self.lyrics,
                'playback': self._playback_payload(),
            }

    def control(self, action, position_sec=None):
        """Play/pause/next/prev/seek on the real player (best effort)."""
        app = (self.song or {}).get('app', '')
        manual = (self.song or {}).get('source') in ('manual', 'acoustid')
        if action == 'toggle' and manual:
            with self._lock:
                self._anchor_pos = self._pos_unlocked()
                self._anchor_time = time.monotonic()
                self.playing = not self.playing
                self._emit_playback()
            return True
        if action == 'seek':
            self.seek(position_sec)
            if not manual:
                control('seek', app, position_sec)
            return True
        return control(action, app)

    def seek(self, position_sec):
        """Move our clock (also used for tap-to-sync when the player can't report position)."""
        with self._lock:
            self._anchor_pos = max(0.0, float(position_sec))
            self._anchor_time = time.monotonic()
            self._emit_playback()

    def set_offset(self, offset_ms):
        with self._lock:
            if not self.song:
                return
            self.song['offset_ms'] = int(offset_ms)
            self.cache._set('offset', self._key, int(offset_ms))
            self.sio.emit('song', self.song)

    def resume_live(self):
        """Leave a manually opened song and follow the player again."""
        with self._lock:
            self._key = None            # next poll treats the player's current song as 'new' -> resync
            self._player_key = None
            self._last_reading = None
            self._last_seen = time.monotonic()
        info = get_media_info()
        return bool(info)

    def play_manual(self, title, artist, album='', artwork='', duration=0):
        """Search-and-play from the UI: no player to follow, clock starts at 0."""
        info = {'title': title, 'artist': artist, 'album': album, 'status': 'playing',
                'position_ms': 0, 'duration_ms': int((duration or 0) * 1000), 'artwork_url': artwork or '', 'source': 'manual',
                'app': 'manual', 'position_known': False}
        with self._lock:
            self._new_song(info)

    # ───────────── loop ─────────────

    def _loop(self):
        misses = 0
        while self._running:
            t0 = time.monotonic()
            try:
                info = get_media_info()
                read_time = (t0 + time.monotonic()) / 2   # reading reflects roughly mid-call
                if info:
                    misses = 0
                    self._last_seen = time.monotonic()
                    self._on_info(info, read_time)
                else:
                    misses += 1
                    self._on_no_info(misses)
            except Exception as e:
                print(f"[Tracker] loop error: {e}")
            # Adaptive cadence: browser tabs are costly to query, and nothing-playing needs no fast poll.
            interval = Config.POLL_INTERVAL
            if misses >= 3:
                interval = 1.5
            elif self._coarse:
                interval = 0.3        # catch the whole-second tick within ~0.3s (cheap: one-tab query)
            elif self.song and self.song.get('source') == 'browser':
                interval = max(interval, 1.0)
            time.sleep(max(0.05, interval - (time.monotonic() - t0)))

    # ───────────── handling ─────────────

    def _on_info(self, info, read_time):
        with self._lock:
            key = song_key(info['title'], info['artist'])
            manual = bool(self.song and self.song.get('source') == 'manual')
            if manual and key == self._player_key:
                return   # a manually searched song stays until the player moves on
            self._player_key = key
            if key != self._key:
                self._new_song(info, read_time)
                return

            # Same song: refresh metadata that may arrive late
            if info.get('duration_ms') and not self.song.get('duration'):
                self.song['duration'] = info['duration_ms'] / 1000.0
            if info.get('artwork_url') and not self.song.get('artwork'):
                self.song['artwork'] = proxied(info['artwork_url'])
                self.sio.emit('song', self.song)

            self._coarse = bool(info.get('coarse'))
            playing = info['status'] == 'playing'
            changed = playing != self.playing
            self.playing = playing
            now = time.monotonic()

            if info.get('position_known', True):
                reading = info['position_ms'] / 1000.0
                stale = (self._last_reading is not None and abs(reading - self._last_reading) < 1e-3 and playing and not changed)
                self._last_reading = reading
                if not stale:
                    # Player positions are sampled at read_time; project to now.
                    reading += (now - read_time) if playing else 0
                    if self._coarse and playing:
                        reading += COARSE_TICK_BIAS   # we just saw the whole second tick over
                    expected = self._pos_at(now) if (self.playing and not changed) else reading
                    drift = reading - expected
                    if changed or abs(drift) > SNAP_THRESHOLD:
                        self._anchor_pos, self._anchor_time = reading, now
                        changed = True
                    elif abs(drift) > NUDGE_THRESHOLD:
                        self._anchor_pos = expected + drift * (COARSE_GAIN if self._coarse else NUDGE_GAIN)
                        self._anchor_time = now
                    if not playing:
                        if abs(reading - self._anchor_pos) > 0.05:
                            changed = True     # seek while paused
                        self._anchor_pos, self._anchor_time = reading, now
            elif changed:
                self._anchor_pos, self._anchor_time = self._pos_at(now), now

            if changed or now - self._last_beat > HEARTBEAT:
                self._emit_playback()

    def _on_no_info(self, misses):
        now = time.monotonic()
        with self._lock:
            if self.song and self.playing and self.song.get('source') != 'manual' \
                    and now - self._last_seen > IDLE_AFTER:
                self._anchor_pos = self._pos_unlocked()
                self._anchor_time = now
                self.playing = False
                self._emit_playback()

        # Audio fingerprint fallback (no player reports metadata)
        if (misses >= 4 and not self._fp_busy and Config.ACOUSTID_API_KEY and Config.FPCALC_PATH
                and now - self._last_fp > Config.FINGERPRINT_INTERVAL):
            self._last_fp = now
            self._fp_busy = True
            threading.Thread(target=self._fingerprint, daemon=True, name='fingerprint').start()

    def _fingerprint(self):
        try:
            wav = capture_system_audio()
            if wav and check_audio_level(wav):
                res = identify_from_audio(wav)
                if res:
                    info = {**res, 'status': 'playing', 'position_ms': 0, 'duration_ms': 0,
                            'artwork_url': '', 'app': 'fingerprint', 'position_known': False}
                    with self._lock:
                        if song_key(info['title'], info['artist']) != self._key:
                            self._new_song(info)
        except Exception as e:
            print(f"[Tracker] fingerprint error: {e}")
        finally:
            self._fp_busy = False

    # ───────────── song lifecycle ─────────────

    def _new_song(self, info, read_time=None):
        now = time.monotonic()
        self._key = song_key(info['title'], info['artist'])
        offset = self.cache._get('offset', self._key) or 0
        self.song = {
            'id': uuid.uuid4().hex[:12],
            'title': info['title'], 'artist': info['artist'], 'album': info.get('album', ''),
            'artwork': proxied(info.get('artwork_url', '')),
            'duration': (info.get('duration_ms') or 0) / 1000.0,
            'source': info.get('source', ''), 'app': info.get('app', ''),
            'offset_ms': offset,
        }
        self.playing = info['status'] == 'playing'
        self.position_known = info.get('position_known', True)
        pos = info['position_ms'] / 1000.0
        self._coarse = bool(info.get('coarse'))
        if self._coarse:
            pos += 0.5            # true position is somewhere in [n, n+1): start in the middle, refine on ticks
        if read_time:
            pos += (now - read_time) if self.playing else 0
        self._anchor_pos, self._anchor_time = pos, now
        self._last_reading = info['position_ms'] / 1000.0
        self.lyrics = {'song_id': self.song['id'], 'status': 'loading', 'lines': [], 'synced': False, 'source': ''}

        print(f"[Tracker] ♪ {self.song['title']} — {self.song['artist']} "
              f"({self.song['app'] or self.song['source']}, pos={pos:.1f}s, dur={self.song['duration']:.0f}s)")
        self.cache.add_to_history(self.song['title'], self.song['artist'], self.song['album'], self.song['artwork'])
        self.sio.emit('song', self.song)
        self.sio.emit('lyrics', self.lyrics)
        self._emit_playback()
        threading.Thread(target=self._load_lyrics, args=(dict(self.song),), daemon=True, name='lyrics').start()

    def _load_lyrics(self, song):
        duration = song['duration'] or None
        data = self.cache.get_lyrics(song['title'], song['artist'], duration)
        if not data:
            data = fetch_lyrics(song['title'], song['artist'], song['album'], duration)
            if data and data.get('lines'):
                self.cache.set_lyrics(song['title'], song['artist'], data, duration)
        with self._lock:
            if not self.song or self.song['id'] != song['id']:
                return   # song changed while we were fetching
            lines = (data or {}).get('lines') or []
            m = (data or {}).get('match')
            if m and m.get('title') and song.get('source') == 'browser':
                # Browser tab titles are ambiguous; show the metadata of the matched track.
                self.song['title'], self.song['artist'] = m['title'], m.get('artist') or ''
                self.sio.emit('song', self.song)
            self.lyrics = {
                'song_id': song['id'],
                'status': 'ready' if lines else 'none',
                'lines': lines,
                'synced': bool((data or {}).get('synced')),
                'source': (data or {}).get('source', ''),
            }
            self.sio.emit('lyrics', self.lyrics)
            self._emit_playback()
            title, artist, album = self.song['title'], self.song['artist'], self.song['album']
            need_art = not self.song.get('artwork')

        if need_art:
            self._load_artwork(song['id'], title, artist, album)

    def _load_artwork(self, song_id, title, artist, album):
        key = 'art|' + song_key(title, artist)
        url = self.cache._get('art', key)
        if url is None:
            url = find_artwork(title, artist, album)
            self.cache._set('art', key, url)      # cache misses too ('') so we don't re-query
        if not url:
            return
        with self._lock:
            if self.song and self.song['id'] == song_id and not self.song.get('artwork'):
                self.song['artwork'] = proxied(url) if proxied(url).startswith('/api/art') else url
                self.cache.set_history_artwork(title, artist, self.song['artwork'])
                self.sio.emit('song', self.song)

    # ───────────── clock ─────────────

    def _pos_at(self, mono):
        if not self.playing:
            return self._anchor_pos
        return self._anchor_pos + (mono - self._anchor_time)

    def _pos_unlocked(self):
        return self._pos_at(time.monotonic())

    def _playback_payload(self):
        return {
            'song_id': self.song['id'] if self.song else None,
            'position_sec': round(self._pos_unlocked(), 3),
            'playing': self.playing,
            'position_known': self.position_known,
            'server_time': time.time(),
        }

    def _emit_playback(self):
        self._last_beat = time.monotonic()
        self.sio.emit('playback', self._playback_payload())
