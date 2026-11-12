import { useEffect } from 'react';
import { io } from 'socket.io-client';
import useStore from './store';
import { clock } from './lib/clock';
import { BACKEND } from './lib/api';

export default function useBackend() {
  useEffect(() => {
    const s = useStore.getState();
    const socket = io(BACKEND || undefined, { transports: ['websocket', 'polling'], reconnectionDelay: 500, reconnectionDelayMax: 3000 });

    socket.on('connect', () => s.setConnected(true));
    socket.on('disconnect', () => s.setConnected(false));
    socket.on('song', (song) => s.setSong(song));
    socket.on('lyrics', (l) => s.setLyrics(l));
    socket.on('playback', (p) => { clock.update(p); s.setPlayback(p); });

    return () => socket.disconnect();
  }, []);
}
