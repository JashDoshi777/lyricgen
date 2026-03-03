"""
Hybrid song detection manager.
Tries Windows SMTC first, falls back to audio fingerprinting.

v2: Added fast position polling thread (500ms) separate from song detection (3s).
"""

import time
import threading
from recognition.media_session import get_media_info
from recognition.fingerprint import identify_from_audio
from audio_capture.capture import capture_system_audio, check_audio_level
from config import Config


class SongDetector:
    """
    Manages song detection using a hybrid approach:
    1. Windows SMTC (instant metadata)
    2. Audio fingerprinting (fallback for apps without SMTC support)

    Runs TWO loops:
    - Song detection loop (every 3s) — expensive, detects new songs
    - Position polling loop (every 500ms) — cheap, tracks playback position
    """

    def __init__(self, socketio=None):
        self.socketio = socketio
        self.current_song = None
        self.is_running = False
        self._detection_thread = None
        self._position_thread = None
        self._lock = threading.Lock()
        self.song_start_time = None
        self.on_song_changed = None      # Callback for new song
        self.on_position_update = None   # Callback for position re-sync
        self.on_status_changed = None    # Callback for pause/resume

        # Track last known status to detect changes in position loop
        self._last_known_status = None
        self._last_position_ms = -1

    def start(self):
        """Start both detection and position polling loops."""
        if self.is_running:
            return
        self.is_running = True

        self._detection_thread = threading.Thread(
            target=self._detection_loop, daemon=True, name="SongDetection"
        )
        self._detection_thread.start()

        self._position_thread = threading.Thread(
            target=self._position_loop, daemon=True, name="PositionPoll"
        )
        self._position_thread.start()

        print("[Detector] Song detection started (detection=3s, position=500ms)")

    def stop(self):
        """Stop all loops."""
        self.is_running = False
        if self._detection_thread:
            self._detection_thread.join(timeout=5)
        if self._position_thread:
            self._position_thread.join(timeout=5)
        print("[Detector] Song detection stopped")

    def _detection_loop(self):
        """Main detection loop — detects new songs (runs every 3s)."""
        while self.is_running:
            try:
                song_info = self._detect()
                if song_info:
                    self._handle_detection(song_info)
            except Exception as e:
                print(f"[Detector] Error in detection loop: {e}")

            time.sleep(Config.DETECTION_INTERVAL)

    def _position_loop(self):
        """
        Fast position polling loop — polls SMTC position every 500ms.
        
        This is separate from song detection because:
        - Song detection is expensive (may involve audio fingerprinting)
        - Position polling is cheap (just reads SMTC timeline)
        - We need fast position updates for accurate sync
        """
        while self.is_running:
            try:
                if self.current_song:
                    media_info = get_media_info()
                    if media_info and media_info.get('title'):
                        position_ms = media_info.get('position_ms', 0)
                        status = media_info.get('status', 'unknown')

                        # Forward position to sync engine
                        if position_ms > 0 and self.on_position_update:
                            self.on_position_update(position_ms)

                        # Detect status changes (pause/resume)
                        if status != self._last_known_status and self._last_known_status is not None:
                            with self._lock:
                                if self.current_song:
                                    self.current_song['status'] = status
                            self._emit_status_event(media_info)
                            if self.on_status_changed:
                                self.on_status_changed(status, position_ms)

                        self._last_known_status = status

            except Exception as e:
                print(f"[Detector] Error in position loop: {e}")

            time.sleep(Config.POSITION_POLL_INTERVAL)

    def _detect(self):
        """
        Try to detect the current song.
        Priority: SMTC → Audio Fingerprint
        """
        # Method 1: Windows SMTC
        media_info = get_media_info()
        if media_info and media_info.get('title'):
            return media_info

        # Method 2: Audio fingerprint fallback
        print("[Detector] SMTC failed, trying audio fingerprint...")
        audio_data = capture_system_audio()

        if audio_data and check_audio_level(audio_data):
            result = identify_from_audio(audio_data)
            if result:
                return result

        return None

    def _handle_detection(self, song_info):
        """Handle a detected song — emit events if it's a new song."""
        with self._lock:
            # Check if song has changed
            if self._is_same_song(song_info):
                # Position updates are now handled by _position_loop
                # Just update status if it changed (backup for position loop)
                if self.current_song and self.current_song.get('status') != song_info.get('status'):
                    new_status = song_info.get('status', 'unknown')
                    self.current_song['status'] = new_status
                    self._emit_status_event(song_info)
                    if self.on_status_changed:
                        self.on_status_changed(new_status, song_info.get('position_ms', 0))
                return

            # New song detected
            self.current_song = song_info
            self.song_start_time = time.time()
            self._last_known_status = song_info.get('status', 'unknown')
            self._last_position_ms = song_info.get('position_ms', 0)
            print(f"[Detector] New song: {song_info.get('title')} — {song_info.get('artist')}")

            # Emit song_detected event
            if self.socketio:
                self.socketio.emit('song_detected', {
                    'title': song_info.get('title', ''),
                    'artist': song_info.get('artist', ''),
                    'album': song_info.get('album', ''),
                    'source': song_info.get('source', 'unknown'),
                    'position_ms': song_info.get('position_ms', 0),
                    'timestamp': time.time()
                })

            # Call callback
            if self.on_song_changed:
                self.on_song_changed(song_info)

    def _is_same_song(self, new_info):
        """Check if the detected song is the same as the current one."""
        if not self.current_song:
            return False
        return (
            self.current_song.get('title', '').lower() == new_info.get('title', '').lower()
            and self.current_song.get('artist', '').lower() == new_info.get('artist', '').lower()
        )

    def _emit_status_event(self, song_info):
        """Emit playback status change events."""
        if not self.socketio:
            return

        status = song_info.get('status', 'unknown')
        position_ms = song_info.get('position_ms', 0)
        if status == 'paused':
            self.socketio.emit('song_paused', {
                'timestamp': time.time(),
                'position_ms': position_ms,
            })
        elif status == 'playing':
            self.socketio.emit('song_resumed', {
                'timestamp': time.time(),
                'position_ms': position_ms,
            })

    def get_current_song(self):
        """Get the currently detected song info."""
        with self._lock:
            return self.current_song

    def get_playback_position(self):
        """Estimate the current playback position in milliseconds."""
        if not self.current_song or not self.song_start_time:
            return 0

        initial_pos = self.current_song.get('position_ms', 0)
        elapsed = (time.time() - self.song_start_time) * 1000
        return int(initial_pos + elapsed)
