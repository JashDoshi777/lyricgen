import { useEffect, useRef, useCallback } from 'react';
import useStore from './useStore';

/**
 * Client-side sync clock — v4.0 (Hybrid Clock)
 *
 * The clock ALWAYS advances when playing. Server position_sync events
 * snap the anchor — if SMTC freezes, our clock just keeps ticking.
 * Only explicit pause freezes it.
 */

const LOOKAHEAD_SEC = 0.2;

export default function useSyncClock() {
    const {
        lyrics,
        synced,
        isPlaying,
        setCurrentLine,
    } = useStore();

    const clockRef = useRef({
        // Anchor-based clock: position = anchorPos + (now - anchorTime)
        anchorPosition: 0,
        anchorTime: 0,      // performance.now() / 1000
        isRunning: false,

        // Lyrics
        lyrics: [],
        durations: [],
        currentIndex: -1,

        // Latency
        latencyMs: 0,
        latencySamples: [],

        // rAF
        rafId: null,
    });

    const getPosition = useCallback(() => {
        const clock = clockRef.current;
        if (!clock.isRunning) return clock.anchorPosition;
        return clock.anchorPosition + (performance.now() / 1000 - clock.anchorTime);
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
            // Resuming — re-anchor from current position
            clock.anchorTime = performance.now() / 1000;
            clock.isRunning = true;
        } else if (!isPlaying && clock.isRunning) {
            // Pausing — save current position as anchor
            clock.anchorPosition = getPosition();
            clock.anchorTime = performance.now() / 1000;
            clock.isRunning = false;
        }
    }, [isPlaying, getPosition]);

    // ── Server Position Sync ──────────────────────

    const handlePositionSync = useCallback((data) => {
        const clock = clockRef.current;
        if (!clock.lyrics.length) return;

        const serverPos = data.position_sec + (clock.latencyMs / 1000);
        const isServerPlaying = data.is_playing;

        // Snap anchor to server position
        clock.anchorPosition = serverPos;
        clock.anchorTime = performance.now() / 1000;
        clock.isRunning = isServerPlaying;
    }, []);

    const handleLyricChanged = useCallback((data) => {
        const clock = clockRef.current;
        if (!clock.lyrics.length) return;

        // Backup sync from lyric_changed
        const serverPos = data.position_sec;
        const myPos = getPosition();
        if (Math.abs(serverPos - myPos) > 0.5) {
            clock.anchorPosition = serverPos;
            clock.anchorTime = performance.now() / 1000;
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
        console.log(`[SyncClock] Reset to ${positionMs}ms`);
    }, []);

    const handlePause = useCallback(() => {
        const clock = clockRef.current;
        clock.anchorPosition = getPosition();
        clock.anchorTime = performance.now() / 1000;
        clock.isRunning = false;
    }, [getPosition]);

    const handleResume = useCallback((data) => {
        const clock = clockRef.current;
        if (data && data.position_ms > 0) {
            clock.anchorPosition = data.position_ms / 1000;
        }
        clock.anchorTime = performance.now() / 1000;
        clock.isRunning = true;
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
