"""
Precision Lyric Sync Engine — v4.0 (Hybrid Clock)
===================================================
Runs its own clock that ALWAYS advances, uses SMTC to correct it.

Key principle: The internal clock never freezes except on explicit pause.
SMTC positions are used to snap/correct the clock, but if SMTC stops
reporting new positions, the clock keeps ticking on its own.

This handles:
- Unreliable SMTC (frozen positions, stale readings) → clock keeps going
- YouTube buffering → detected via PAUSE status, not position freezing
- Seeks / fast-forward → large position jump = instant snap
- Laggy devices → clock is lightweight, runs smoothly
"""

import time
import threading

# ── Tuning Constants ────────────────────────────────

# Show lyrics slightly AHEAD of the song
LOOKAHEAD_SEC = 0.5

# Position broadcast interval (seconds)
POSITION_BROADCAST_INTERVAL = 0.15

# Sync loop tick interval — ~60fps
SYNC_TICK_INTERVAL = 0.016


class SyncEngine:
    """
    Hybrid clock sync engine.

    The clock always ticks at 1x speed when playing.
    Every new SMTC position reading: snap the clock to it.
    Same SMTC position: ignored (clock keeps ticking on its own).
    Pause/resume: handled via explicit status callbacks.
    """

    def __init__(self, socketio):
        self.socketio = socketio

        # ── Lyrics ──
        self.lyrics = []
        self.current_index = -1

        # ── Clock ──
        # Position = anchor_position + (now - anchor_time)
        self._anchor_position = 0.0    # known song position (seconds)
        self._anchor_time = 0.0        # monotonic time of that anchor

        # ── State ──
        self.is_syncing = False
        self.is_paused = False
        self._paused_position = 0.0
        self._lock = threading.Lock()

        # ── SMTC ──
        self._last_smtc_ms = -1

        # ── Threads ──
        self._sync_thread = None
        self._broadcast_thread = None

    # ── Public API ──────────────────────────────────

    def start_sync(self, lyrics, position_ms=0):
        """Start sync with an initial position estimate."""
        self.stop_sync()

        with self._lock:
            self.lyrics = lyrics
            self.current_index = -1
            self.is_paused = False
            self._last_smtc_ms = -1

            pos_sec = position_ms / 1000.0
            self._anchor_position = pos_sec
            self._anchor_time = time.monotonic()
            self._find_current_index(pos_sec + LOOKAHEAD_SEC)
            self._pending_backward = None

            print(f"[SyncEngine] Started: {len(lyrics)} lines, pos={position_ms}ms")

        self.is_syncing = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True, name="SyncLoop")
        self._sync_thread.start()
        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True, name="BroadcastLoop")
        self._broadcast_thread.start()

        self._emit_lyrics_loaded()
        if self.current_index >= 0:
            self._emit_current_line()

    def resync(self, position_ms):
        """
        Process a new SMTC position reading.

        Smart rules to avoid snapping to stale/bad positions:
        - position=0 when we're past 5s → reject (session lost)
        - Backward jump >1s → only accept if confirmed by 2 consecutive readings
        - Forward correction → always accept
        - Small drift (<1s) → always accept
        """
        with self._lock:
            if not self.lyrics:
                return
            if self.is_paused:
                return

            # Skip identical readings — SMTC hasn't updated
            if position_ms == self._last_smtc_ms:
                return

            now = time.monotonic()
            smtc_sec = position_ms / 1000.0
            our_position = self._get_position_unlocked()
            drift = smtc_sec - our_position  # positive = forward, negative = backward

            self._last_smtc_ms = position_ms

            # ── Rule 1: Reject position=0 when we're past 5s ──
            # This happens when SMTC session is lost (tab closed, player crashed)
            if position_ms == 0 and our_position > 5.0:
                print(f"[SyncEngine] Rejected pos=0 (session lost? our_pos={our_position:.1f}s)")
                return

            # ── Rule 2: Handle backward jumps ──
            if drift < -1.0:
                # Large backward jump — could be frozen SMTC or a real seek
                # Only accept if we've seen a similar backward position before
                if self._pending_backward is None:
                    self._pending_backward = smtc_sec
                    self._pending_backward_count = 1
                    print(f"[SyncEngine] Backward {drift:+.1f}s → pending confirmation (SMTC={smtc_sec:.1f}s)")
                    return
                elif abs(smtc_sec - self._pending_backward) < 2.0:
                    self._pending_backward_count += 1
                    if self._pending_backward_count >= 2:
                        # Confirmed — it's a real seek backward
                        print(f"[SyncEngine] Backward CONFIRMED → snap to {smtc_sec:.1f}s")
                        self._pending_backward = None
                        # Fall through to snap
                    else:
                        return
                else:
                    # Different backward position — reset pending
                    self._pending_backward = smtc_sec
                    self._pending_backward_count = 1
                    return
            else:
                # Forward or small drift — clear any pending backward
                self._pending_backward = None

            # ── Snap to the position ──
            self._anchor_position = smtc_sec
            self._anchor_time = now

            if abs(drift) > 0.3:
                direction = "FWD" if drift > 0 else "BWD"
                print(f"[SyncEngine] {direction}: {our_position:.1f}s → {smtc_sec:.1f}s (drift={drift:+.2f}s)")

            # Update line if needed
            new_pos = smtc_sec + LOOKAHEAD_SEC
            old_index = self.current_index
            self._find_current_index(new_pos)
            if self.current_index != old_index:
                self._emit_current_line()

    def stop_sync(self):
        """Stop the sync engine."""
        self.is_syncing = False
        if self._sync_thread:
            self._sync_thread.join(timeout=2)
            self._sync_thread = None
        if self._broadcast_thread:
            self._broadcast_thread.join(timeout=2)
            self._broadcast_thread = None

    def pause(self):
        """Pause — freeze clock at current position."""
        with self._lock:
            if not self.is_paused:
                self._paused_position = self._get_position_unlocked()
                self.is_paused = True
                print(f"[SyncEngine] Paused at {self._paused_position:.1f}s")

    def resume(self, position_ms=None):
        """Resume — restart clock from given or paused position."""
        with self._lock:
            if self.is_paused:
                if position_ms is not None and position_ms > 0:
                    resume_pos = position_ms / 1000.0
                else:
                    resume_pos = self._paused_position

                self._anchor_position = resume_pos
                self._anchor_time = time.monotonic()
                self.is_paused = False
                self._last_smtc_ms = -1  # allow next SMTC reading to correct

                old_index = self.current_index
                self._find_current_index(resume_pos + LOOKAHEAD_SEC)
                if self.current_index != old_index:
                    self._emit_current_line()
                print(f"[SyncEngine] Resumed at {resume_pos:.1f}s")

    def emit_current_state(self):
        """Re-emit full state for client reconnection."""
        with self._lock:
            if not self.lyrics:
                return
            self._emit_lyrics_loaded()
            if not self.is_paused:
                pos = self._get_position_unlocked()
                self._find_current_index(pos + LOOKAHEAD_SEC)
            if self.current_index >= 0:
                self._emit_current_line()

    def get_position_ms(self):
        """Get estimated current position in ms."""
        with self._lock:
            return int(self._get_position_unlocked() * 1000)

    # ── Internal: Position ──────────────────────────

    def _get_position_unlocked(self):
        """Get current position (must hold lock)."""
        if self.is_paused:
            return self._paused_position
        return self._anchor_position + (time.monotonic() - self._anchor_time)

    # ── Internal: Loops ─────────────────────────────

    def _sync_loop(self):
        """60fps line change detection. Clock always advances."""
        while self.is_syncing:
            if not self.is_paused and self.lyrics:
                self._check_lyric_change()
            time.sleep(SYNC_TICK_INTERVAL)

    def _broadcast_loop(self):
        """Position broadcasts for client-side clock."""
        while self.is_syncing:
            if self.lyrics:
                with self._lock:
                    pos = self._get_position_unlocked()

                self.socketio.emit('position_sync', {
                    'position_sec': round(pos, 3),
                    'server_time': time.time(),
                    'is_playing': not self.is_paused,
                    'current_index': self.current_index,
                })
            time.sleep(POSITION_BROADCAST_INTERVAL)

    def _check_lyric_change(self):
        """Check if the active line should change."""
        with self._lock:
            if not self.lyrics:
                return
            pos = self._get_position_unlocked() + LOOKAHEAD_SEC
            new_index = self._calc_line_index(pos)
            if new_index != self.current_index:
                self.current_index = new_index
                self._emit_current_line()

    # ── Internal: Helpers ───────────────────────────

    def _find_current_index(self, position_sec):
        self.current_index = self._calc_line_index(position_sec)

    def _calc_line_index(self, position_sec):
        """Binary search: last line where time <= position."""
        if not self.lyrics:
            return -1
        lo, hi = 0, len(self.lyrics) - 1
        result = -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.lyrics[mid]['time'] <= position_sec:
                result = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return result

    def _emit_current_line(self):
        """Emit current lyric line."""
        if self.current_index < 0 or self.current_index >= len(self.lyrics):
            return

        line = self.lyrics[self.current_index]

        if self.current_index + 1 < len(self.lyrics):
            duration_ms = int((self.lyrics[self.current_index + 1]['time'] - line['time']) * 1000)
        else:
            duration_ms = 5000
        duration_ms = max(500, min(duration_ms, 30000))

        line_progress = 0.0
        pos = self._get_position_unlocked()
        if duration_ms > 0:
            line_progress = max(0.0, min(1.0, (pos - line['time']) / (duration_ms / 1000.0)))

        prev_lines = [self.lyrics[i] for i in range(max(0, self.current_index - 3), self.current_index)]
        next_lines = [self.lyrics[i] for i in range(self.current_index + 1, min(len(self.lyrics), self.current_index + 4))]

        self.socketio.emit('lyric_changed', {
            'index': self.current_index,
            'line': line,
            'duration_ms': duration_ms,
            'progress': round(line_progress, 3),
            'previous': prev_lines,
            'next': next_lines,
            'total': len(self.lyrics),
            'position_sec': round(pos, 3),
            'server_time': time.time(),
        })

    def _emit_lyrics_loaded(self):
        """Emit full lyrics with pre-computed durations and current position."""
        line_durations = []
        for i, line in enumerate(self.lyrics):
            if i + 1 < len(self.lyrics):
                dur = int((self.lyrics[i + 1]['time'] - line['time']) * 1000)
            else:
                dur = 5000
            line_durations.append(max(500, min(dur, 30000)))

        # Include current position so the client can reset its clock accurately
        current_pos = self._get_position_unlocked()

        self.socketio.emit('lyrics_loaded', {
            'lyrics': self.lyrics,
            'durations': line_durations,
            'synced': any(l.get('time', 0) > 0 for l in self.lyrics),
            'total': len(self.lyrics),
            'position_sec': round(current_pos, 3),
            'server_time': time.time(),
        })
