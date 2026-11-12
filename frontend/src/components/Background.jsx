import { useEffect, useRef, useState } from 'react';
import useStore from '../store';
import { artSrc } from '../lib/api';
import { artworkPalette, hashPalette } from '../lib/color';

// Apple-Music-style backdrop: the album cover, hugely blurred and slowly drifting.
// Cross-fades between songs. Transforms only, so the heavy blur is rendered once.
export default function Background() {
  const song = useStore((s) => s.song);
  const playing = useStore((s) => s.playing);
  const art = song?.artwork ? artSrc(song.artwork) : '';
  const [pal, setPal] = useState(['#3b2a8f', '#8f2a6b']);
  const [layers, setLayers] = useState([]);       // [{url, id}] newest last
  const seq = useRef(0);

  useEffect(() => {
    if (!song) return;
    let dead = false;
    artworkPalette(art).then((p) => {
      if (dead) return;
      const colors = p || hashPalette(song.title + song.artist);
      setPal(colors);
      const root = document.documentElement.style;
      root.setProperty('--c1', colors[0]);
      root.setProperty('--c2', colors[1]);
    });
    return () => { dead = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [song?.id, art]);

  useEffect(() => {
    if (!art) { setLayers([]); return; }
    const img = new Image();
    let dead = false;
    img.onload = () => {
      if (dead) return;
      const id = ++seq.current;
      setLayers((l) => [...l.slice(-1), { url: art, id }]);
      setTimeout(() => setLayers((l) => l.filter((x) => x.id >= id)), 1600);   // drop the old one after the fade
    };
    img.src = art;
    return () => { dead = true; };
  }, [art]);

  return (
    <div className={`bg${playing ? ' live' : ''}`} style={{ '--c1': pal[0], '--c2': pal[1] }}>
      {!layers.length && <><i className="blob b1" /><i className="blob b2" /><i className="blob b3" /></>}
      {layers.map((l) => (
        <div className="art-wrap" key={l.id}>
          <i className="art a1" style={{ backgroundImage: `url(${l.url})` }} />
          <i className="art a2" style={{ backgroundImage: `url(${l.url})` }} />
        </div>
      ))}
      <div className="bg-shade" />
    </div>
  );
}
