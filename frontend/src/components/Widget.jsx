import { useEffect, useRef, useState } from 'react';
import useStore from '../store';
import { Icon } from './Icons';
import LyricsView from './LyricsView';
import Background from './Background';
import { post, artSrc } from '../lib/api';
import { clock } from '../lib/clock';

function Hairline() {
  const ref = useRef(null);
  const dur = useStore((s) => s.song?.duration || 0);
  useEffect(() => {
    const win = ref.current?.ownerDocument?.defaultView || window;
    const set = () => { if (ref.current) ref.current.style.transform = `scaleX(${dur ? Math.min(1, clock.position() / dur) : 0})`; };
    set();
    const id = win.setInterval(set, 250);     // CSS transition smooths the gaps: far cheaper than per-frame
    return () => win.clearInterval(id);
  }, [dur]);
  return <div className="w-hair"><i ref={ref} /></div>;
}

// Compact, resizable overlay used by BOTH the Electron desktop widget and the in-browser
// Picture-in-Picture pop-out. The same LyricsView adapts to any window size.
export default function Widget({ onClose }) {
  const song = useStore((s) => s.song);
  const playing = useStore((s) => s.playing);
  const fontScale = useStore((s) => s.fontScale);
  const [opacity, setOpacity] = useState(() => Number(localStorage.getItem('ll.opacity') || 0.82));
  const root = useRef(null);
  const api = window.electronAPI;

  useEffect(() => {
    root.current?.ownerDocument.documentElement.style.setProperty('--fs', fontScale);
  }, [fontScale]);

  // Transparent frameless windows can't be resized natively on Windows: custom grip.
  const startResize = (e) => {
    e.preventDefault();
    let lx = e.screenX, ly = e.screenY;
    const move = (ev) => { api.resizeBy(ev.screenX - lx, ev.screenY - ly); lx = ev.screenX; ly = ev.screenY; };
    const up = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  };

  return (
    <div className={`widget${api ? ' electron' : ''}`} ref={root} style={{ '--wo': api ? opacity : 1 }}>
      <Background transparent />
      <div className="w-bar">
        <div className="w-id">
          {song?.artwork && <img className="w-art" src={artSrc(song.artwork)} alt="" />}
          <div className="w-title">{song ? <><b>{song.title}</b><span>{song.artist}</span></> : <b>LiveLyrics</b>}</div>
        </div>
        <div className="w-actions">
          <button onClick={() => post('/api/control', { action: 'prev' })} title="Previous"><Icon name="prev" size={15} /></button>
          <button onClick={() => post('/api/control', { action: 'toggle' })} title="Play / pause"><Icon name={playing ? 'pause' : 'play'} size={15} /></button>
          <button onClick={() => post('/api/control', { action: 'next' })} title="Next"><Icon name="next" size={15} /></button>
          {api && <input type="range" min="0.25" max="1" step="0.05" value={opacity} title="Opacity"
            onChange={(e) => { setOpacity(+e.target.value); localStorage.setItem('ll.opacity', e.target.value); }} />}
          {api && <button title="Keep on top" onClick={() => api.togglePin()}><Icon name="pin" size={14} /></button>}
          {(api || onClose) && <button title="Close" onClick={() => (api ? api.close() : onClose())}><Icon name="close" size={14} /></button>}
        </div>
      </div>
      <div className="w-body"><LyricsView /></div>
      <Hairline />
      {api && <div className="w-grip" onPointerDown={startResize} />}
    </div>
  );
}
