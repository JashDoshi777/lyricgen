import { useEffect, useRef, useCallback } from 'react';
import useStore from './useStore';

/**
 * Client-side sync clock — v5.0 (Adaptive Speed Clock)
 *
 * The clock ALWAYS advances when playing. Instead of hard-snapping to
 * server position (which causes jarring jumps), the clock adjusts its
 * SPEED to smoothly converge on the correct position:
 *
 *   - Behind by >0.5s → run at 1.15x speed (catches up)
 *   - Ahead by >0.5s → run at 0.85x speed (slows down)
 *   - Within ±0.5s → run at 1.0x (normal)
 *
 * This is "clock recovery" — the same approach used by professional
 * media players and audio synchronization systems.
 */

const LOOKAHEAD_SEC = 0.5;

// Adaptive speed constants
const DRIFT_THRESHOLD = 0.3; // Start correcting at 0.3s drift
const SNAP_THRESHOLD = 2.0;  // Hard-snap above 2s (was 3s — too slow)

export default function useSyncClock() {
    const {
        lyrics,
        synced,
        isPlaying,
        setCurrentLine,
    } = useStore();

    const clockRef = useRef({
        // Anchor-based clock: position = anchorPos + elapsed * speed
        anchorPosition: 0,
        anchorTime: 0,      // performance.now() / 1000
        isRunning: false,
        speed: 1.0,         // Adaptive clock speed

        // Lyrics
        lyrics: [],
        durations: [],
        currentIndex: -1,

        // Latency
        latencyMs: 0,
        latencySamples: [],

        // Server position for drift comparison
        lastServerPos: 0,
        lastServerTime: 0,   // performance.now() / 1000 when received

        // rAF
        rafId: null,
    });

    const getPosition = useCallback(() => {
        const clock = clockRef.current;
        if (!clock.isRunning) return clock.anchorPosition;
        const elapsed = performance.now() / 1000 - clock.anchorTime;
        return clock.anchorPosition + elapsed * clock.speed;
    }, []);

    // ── rAF Tick ──────────────────────────────────

    const tick = useCallback(() => {
        const clock = clockRef.current;

        if (clock.isRunning && clock.lyrics.length) {
            const pos = getPosition() + LOOKAHEAD_SEC;
            const newIndex = binarySearchLine(clock.lyrics, pos);

            if (newIndex !== clock.currentIndex) {
                clock.currentIndex = newIndex;

                const prev = [];
                const next = [];
                for (let i = Math.max(0, newIndex - 3); i < newIndex; i++) {
                    prev.push(clock.lyrics[i]);
                }
                for (let i = newIndex + 1; i < Math.min(clock.lyrics.length, newIndex + 4); i++) {
                    next.push(clock.lyrics[i]);
                }

                const duration = newIndex >= 0 && newIndex < clock.durations.length
                    ? clock.durations[newIndex]
                    : 3000;

                setCurrentLine(newIndex, prev, next, duration);
            }
        }

        clock.rafId = requestAnimationFrame(tick);
    }, [setCurrentLine, getPosition]);

    // ── Start / Stop ──────────────────────────────

    useEffect(() => {
        const clock = clockRef.current;

        if (synced && lyrics.length > 0) {
            clock.lyrics = lyrics;
            clock.durations = lyrics.map((line, i) => {
                if (i + 1 < lyrics.length) {
                    const dur = Math.round((lyrics[i + 1].time - line.time) * 1000);
                    return Math.max(500, Math.min(dur, 30000));
                }
                return 5000;
            });

            // Force re-evaluation on new lyrics
            clock.currentIndex = -1;

            if (!clock.rafId) {
                clock.isRunning = true;
                clock.rafId = requestAnimationFrame(tick);
            }
        }

        return () => {
            if (clock.rafId) {
                cancelAnimationFrame(clock.rafId);
                clock.rafId = null;
            }
        };
    }, [lyrics, synced, tick]);

    useEffect(() => {
        const clock = clockRef.current;
        if (isPlaying && !clock.isRunning) {
            clock.anchorTime = performance.now() / 1000;
            clock.isRunning = true;
        } else if (!isPlaying && clock.isRunning) {
            clock.anchorPosition = getPosition();
            clock.anchorTime = performance.now() / 1000;
            clock.isRunning = false;
        }
    }, [isPlaying, getPosition]);

    // ── Server Position Sync (Adaptive Speed) ─────

    const handlePositionSync = useCallback((data) => {
        const clock = clockRef.current;
        if (!clock.lyrics.length) return;

        const now = performance.now() / 1000;
        const serverPos = data.position_sec + (clock.latencyMs / 1000);
        const isServerPlaying = data.is_playing;

        // Get our current position
        const ourPos = getPosition();
        const drift = serverPos - ourPos; // positive = we're behind, negative = we're ahead

        // Store for reference
        clock.lastServerPos = serverPos;
        clock.lastServerTime = now;

        if (!isServerPlaying) {
            // Server paused — freeze our clock
            clock.anchorPosition = ourPos;
            clock.anchorTime = now;
            clock.isRunning = false;
            clock.speed = SPEED_NORMAL;
            return;
        }

        if (Math.abs(drift) > SNAP_THRESHOLD) {
            // Huge drift (>2s) — hard-snap immediately (seek or stall recovery)
            clock.anchorPosition = serverPos;
            clock.anchorTime = now;
            clock.speed = 1.0;
            console.log(`[SyncClock] SNAP: ${ourPos.toFixed(1)}s → ${serverPos.toFixed(1)}s (drift=${drift.toFixed(1)}s)`);
        } else if (drift > DRIFT_THRESHOLD) {
            // We're behind — proportional speed up (bigger drift = faster)
            // Maps drift 0.3-2.0 → speed 1.3-2.0
            const speedBoost = 1.0 + Math.min(drift, 2.0);
            clock.anchorPosition = ourPos;
            clock.anchorTime = now;
            clock.speed = speedBoost;
        } else if (drift < -DRIFT_THRESHOLD) {
            // We're ahead — proportional slow down
            const absDrift = Math.abs(drift);
            const speedSlow = Math.max(0.3, 1.0 - absDrift * 0.5);
            clock.anchorPosition = ourPos;
            clock.anchorTime = now;
            clock.speed = speedSlow;
        } else {
            // Within tolerance — normal speed
            clock.anchorPosition = ourPos;
            clock.anchorTime = now;
            clock.speed = 1.0;
        }

        clock.isRunning = isServerPlaying;
    }, [getPosition]);

    const handleLyricChanged = useCallback((data) => {
        // Backup sync from lyric_changed — only for large drift
        const clock = clockRef.current;
        if (!clock.lyrics.length) return;

        const serverPos = data.position_sec;
        const myPos = getPosition();
        if (Math.abs(serverPos - myPos) > SNAP_THRESHOLD) {
            clock.anchorPosition = serverPos;
            clock.anchorTime = performance.now() / 1000;
            clock.speed = SPEED_NORMAL;
        }
    }, [getPosition]);

    const handlePongSync = useCallback((data) => {
        const clock = clockRef.current;
        const rtt = Date.now() - data.client_time;
        clock.latencySamples.push(rtt);
        if (clock.latencySamples.length >= 3) {
            const sorted = [...clock.latencySamples].sort((a, b) => a - b);
            clock.latencyMs = sorted[Math.floor(sorted.length / 2)] / 2;
            console.log(`[SyncClock] Latency: ${clock.latencyMs.toFixed(0)}ms`);
        }
    }, []);

    const resetClock = useCallback((positionMs = 0) => {
        const clock = clockRef.current;
        clock.anchorPosition = positionMs / 1000;
        clock.anchorTime = performance.now() / 1000;
        clock.currentIndex = -1;
        clock.isRunning = true;
        clock.speed = SPEED_NORMAL;
        console.log(`[SyncClock] Reset to ${positionMs}ms`);
    }, []);

    const handlePause = useCallback(() => {
        const clock = clockRef.current;
        clock.anchorPosition = getPosition();
        clock.anchorTime = performance.now() / 1000;
        clock.isRunning = false;
        clock.speed = SPEED_NORMAL;
    }, [getPosition]);

    const handleResume = useCallback((data) => {
        const clock = clockRef.current;
        if (data && data.position_ms > 0) {
            clock.anchorPosition = data.position_ms / 1000;
        }
        clock.anchorTime = performance.now() / 1000;
        clock.isRunning = true;
        clock.speed = SPEED_NORMAL;
    }, []);

    return {
        handlePositionSync,
        handleLyricChanged,
        handlePongSync,
        resetClock,
        handlePause,
        handleResume,
        clockRef,
    };
}

function binarySearchLine(lyrics, position) {
    if (!lyrics.length) return -1;
    let lo = 0, hi = lyrics.length - 1, result = -1;
    while (lo <= hi) {
        const mid = (lo + hi) >>> 1;
        if (lyrics[mid].time <= position) {
            result = mid;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return result;
}
