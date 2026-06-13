import { useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import useStore from './useStore';
import useSyncClock from './useSyncClock';

const BACKEND_URL = 'http://localhost:5000';

export default function useSocket() {
    const socketRef = useRef(null);
    const {
        setCurrentSong,
        setLyrics,
        setCurrentLine,
        setConnected,
        setHistory,
        setIsPlaying,
    } = useStore();

    const {
        handlePositionSync,
        handleLyricChanged,
        handlePongSync,
        resetClock,
        handlePause,
        handleResume,
        clockRef,
    } = useSyncClock();

    useEffect(() => {
        const socket = io(BACKEND_URL, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: Infinity,
        });

        socketRef.current = socket;

        socket.on('connect', () => {
            console.log('[WS] Connected to backend');
            setConnected(true);
            socket.emit('request_current');

            // Measure latency — send 3 pings
            for (let i = 0; i < 3; i++) {
                setTimeout(() => {
                    socket.emit('ping_sync', { client_time: Date.now() });
                }, i * 200);
            }
        });

        socket.on('disconnect', () => {
            console.log('[WS] Disconnected');
            setConnected(false);
        });

        socket.on('song_detected', (data) => {
            console.log('[WS] Song detected:', data);
            setCurrentSong(data);
            setIsPlaying(true);
            // DON'T reset clock here — position is stale from detection time.
            // Clock will be reset when lyrics_loaded arrives with fresh position.
            fetch(`${BACKEND_URL}/api/history`)
                .then((r) => r.json())
                .then((d) => setHistory(d.history || []))
                .catch(() => { });
        });

        socket.on('lyrics_loaded', (data) => {
            console.log('[WS] Lyrics loaded:', data.total, 'lines, synced:', data.synced, 'pos:', data.position_sec);
            setLyrics(data.lyrics || [], data.synced || false, data.durations || []);

            // Reset clock with compensation for pipeline delay:
            // 1. Network latency (measured via ping/pong)
            // 2. React render time (~300ms estimate)
            // Without this, lyrics always start behind because the position
            // is already stale by the time the user sees the first lyric.
            const serverPos = (data.position_sec || 0) * 1000;
            const networkLatency = clockRef.current?.latencyMs || 150;
            const renderDelay = 300;
            const compensatedPos = serverPos + networkLatency + renderDelay;
            console.log(`[WS] Clock reset: server=${serverPos.toFixed(0)}ms + latency=${networkLatency.toFixed(0)}ms + render=${renderDelay}ms = ${compensatedPos.toFixed(0)}ms`);
            resetClock(compensatedPos);
        });

        socket.on('lyric_changed', (data) => {
            // The client-side sync clock handles line changes locally,
            // but we still use server events for calibration
            handleLyricChanged(data);
        });

        socket.on('position_sync', (data) => {
            // Fast position updates for client-side interpolation
            handlePositionSync(data);
        });

        socket.on('pong_sync', (data) => {
            handlePongSync(data);
        });

        socket.on('song_paused', (data) => {
            console.log('[WS] Song paused');
            setIsPlaying(false);
            handlePause(data);
        });

        socket.on('song_resumed', (data) => {
            console.log('[WS] Song resumed');
            setIsPlaying(true);
            handleResume(data);
        });

        return () => {
            socket.disconnect();
        };
    }, []);

    return socketRef;
}
