import { useEffect, useRef } from 'react';
import useStore from '../store';
import { clock } from '../lib/clock';
import { post, artSrc } from '../lib/api';
import { Icon } from './Icons';

const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

export default function PlayerBar() {
  const song = useStore((s) => s.song);
  const playing = useStore((s) => s.playing);
  const known = useStore((s) => s.positionKnown);
  const fill = useRef(null);
  const cur = useRef(null);
  const dur = song?.duration || 0;

  useEffect(() => {
    let lastSec = -1;
    const set = () => {
      const p = clock.position();
      if (fill.current) fill.current.style.transform = `scaleX(${dur ? Math.min(1, p / dur) : 0})`;
      const sec = Math.floor(p);
      if (cur.current && sec !== lastSec) { lastSec = sec; cur.current.textContent = fmt(p); }
    };
    set();
    const id = setInterval(set, 250);
    return () => clearInterval(id);
  }, [dur]);

  const ctl = (action) => post('/api/control', { action });
  const seekTo = (e) => {
    if (!dur) return;
    const r = e.currentTarget.getBoundingClientRect();
    post('/api/seek', { position_sec: ((e.clientX - r.left) / r.width) * dur });
  };

  return (
    <div className="pb">
      <div className="pb-art" style={song?.artwork ? { backgroundImage: `url(${artSrc(song.artwork)})` } : undefined}>
        {!song?.artwork && <Icon name="note" size={26} />}
      </div>
      <div className="pb-meta">
        <div className="pb-title">{song ? song.title : 'Waiting for music…'}</div>
        <div className="pb-artist">
          {song ? song.artist || song.album : 'Play something in Spotify, Apple Music, YouTube…'}
          {song?.source === 'manual'
            ? <button className="chip live" onClick={() => post('/api/live')}><span className="dot" /> Back to live</button>
            : song && !known && <span className="chip">tap a lyric to sync</span>}
        </div>
        <div className="pb-prog" onClick={seekTo}>
          <div className="pb-fill" ref={fill} />
        </div>
        <div className="pb-times"><span ref={cur}>0:00</span><span>{dur ? fmt(dur) : ''}</span></div>
      </div>
      <div className="pb-ctl">
        <button onClick={() => ctl('prev')} title="Previous"><Icon name="prev" /></button>
        <button className="play" onClick={() => ctl('toggle')} title={playing ? 'Pause' : 'Play'}><Icon name={playing ? 'pause' : 'play'} /></button>
        <button onClick={() => ctl('next')} title="Next"><Icon name="next" /></button>
      </div>
    </div>
  );
}
