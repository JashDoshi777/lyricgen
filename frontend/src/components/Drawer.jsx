import { useEffect, useRef, useState } from 'react';
import useStore from '../store';
import { get, post, BACKEND, artSrc } from '../lib/api';
import { hashPalette } from '../lib/color';
import { Icon } from './Icons';

const fmtDur = (s) => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}` : '');

// Cover with a tasteful fallback tile (hash-coloured gradient + initial)
function Cover({ src, title, size = 52 }) {
  const [bad, setBad] = useState(false);
  const [c1, c2] = hashPalette(title || '?');
  return src && !bad ? (
    <img className="cover" style={{ width: size, height: size }} src={artSrc(src)} alt="" loading="lazy" onError={() => setBad(true)} />
  ) : (
    <div className="cover fallback" style={{ width: size, height: size, background: `linear-gradient(135deg, ${c1}, ${c2})` }}>
      {(title || '?').trim()[0]?.toUpperCase()}
    </div>
  );
}

function Switch({ checked, onChange }) {
  return <button role="switch" aria-checked={checked} className={`sw${checked ? ' on' : ''}`} onClick={() => onChange(!checked)}><i /></button>;
}

function playSong(s) {
  const q = new URLSearchParams({ title: s.title, artist: s.artist || '', album: s.album || '',
    artwork: s.artwork || '', duration: s.duration || 0 });
  return get(`/api/search?${q}`);
}

// ───────────────── Search with live suggestions ─────────────────
function Search({ close }) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sel, setSel] = useState(0);
  const [searched, setSearched] = useState(false);
  const input = useRef(null);

  useEffect(() => { get('/api/history?limit=8').then((d) => setRecent(dedupe(d.history || []).slice(0, 6))).catch(() => {}); }, []);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) return;
    const ctl = new AbortController();
    const t = setTimeout(() => {
      setLoading(true);
      fetch(`${BACKEND}/api/suggest?q=${encodeURIComponent(term)}`, { signal: ctl.signal })
        .then((r) => r.json()).then((d) => { setResults(d.results || []); setSel(0); setLoading(false); setSearched(true); })
        .catch((e) => { if (e.name !== 'AbortError') setLoading(false); });
    }, 220);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [q]);

  const list = q.trim().length >= 2 ? results : recent;
  const choose = async (s) => { await playSong(s); close(); };
  const onKey = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSel((i) => Math.min(list.length - 1, i + 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSel((i) => Math.max(0, i - 1)); }
    else if (e.key === 'Enter' && list[sel]) choose(list[sel]);
  };

  return (
    <>
      <div className="search-field">
        <Icon name="search" size={18} />
        <input ref={input} autoFocus value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKey}
          placeholder="Songs, artists" spellCheck={false} />
        {q && <button className="clear" onClick={() => { setQ(''); input.current?.focus(); }} aria-label="Clear"><Icon name="close" size={11} /></button>}
      </div>

      {q.trim().length < 2 && recent.length > 0 && <div className="group-title">Recent</div>}
      {q.trim().length >= 2 && loading && !results.length && (
        <div className="group">{[0, 1, 2, 3].map((i) => (
          <div className="res skel" key={i}><div className="cover sk" /><div className="sk-lines"><i /><i /></div></div>
        ))}</div>
      )}
      {!loading && q.trim().length >= 2 && !results.length && searched && <p className="empty-note">No songs found for “{q.trim()}”.</p>}
      {q.trim().length < 2 && !recent.length && <p className="empty-note">Search any song to see its lyrics, even when nothing is playing.</p>}

      {list.length > 0 && (
        <div className="group results">
          {list.map((s, i) => (
            <button key={`${s.title}|${s.artist}|${i}`} className={`res${i === sel ? ' on' : ''}`}
              onMouseEnter={() => setSel(i)} onClick={() => choose(s)}>
              <Cover src={s.thumb || s.artwork} title={s.title} />
              <div className="res-meta">
                <div className="res-title">{s.title}{s.explicit && <span className="exp">E</span>}</div>
                <div className="res-sub">{[s.artist, s.album].filter(Boolean).join(' · ')}</div>
              </div>
              <div className="res-end">{fmtDur(s.duration)}</div>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function dedupe(items) {
  const seen = new Set();
  return items.filter((h) => { const k = `${h.title}|${h.artist}`; if (seen.has(k)) return false; seen.add(k); return true; });
}

// ───────────────── History ─────────────────
function History({ close }) {
  const [items, setItems] = useState(null);
  useEffect(() => { get('/api/history').then((d) => setItems(dedupe(d.history || []))).catch(() => setItems([])); }, []);
  if (!items) return <div className="group">{[0, 1, 2].map((i) => <div className="res skel" key={i}><div className="cover sk" /><div className="sk-lines"><i /><i /></div></div>)}</div>;
  return (
    <>
      {!items.length && <p className="empty-note">Songs you listen to will show up here.</p>}
      {items.length > 0 && (
        <div className="group results">
          {items.map((h, i) => (
            <button key={i} className="res" onClick={async () => { await playSong({ ...h, artwork: '' }); close(); }}>
              <Cover src={h.artwork} title={h.title} />
              <div className="res-meta"><div className="res-title">{h.title}</div><div className="res-sub">{h.artist}</div></div>
              <div className="res-end">{ago(h.played_at)}</div>
            </button>
          ))}
        </div>
      )}
      {items.length > 0 && (
        <div className="group" style={{ marginTop: 18 }}>
          <button className="row-item danger" onClick={async () => { await fetch(BACKEND + '/api/history', { method: 'DELETE' }); setItems([]); }}>Clear History</button>
        </div>
      )}
    </>
  );
}

function ago(ts) {
  const m = Math.max(0, Math.round((Date.now() / 1000 - ts) / 60));
  if (m < 1) return 'now'; if (m < 60) return `${m}m`; if (m < 1440) return `${Math.round(m / 60)}h`; return `${Math.round(m / 1440)}d`;
}

// ───────────────── Settings ─────────────────
function Tile({ color, children }) { return <div className="tile" style={{ background: color }}>{children}</div>; }

function Settings() {
  const st = useStore();
  const [langs, setLangs] = useState({});
  useEffect(() => { get('/api/languages').then(setLangs).catch(() => {}); }, []);
  const off = st.song?.offset_ms || 0;
  const setOff = (v) => post('/api/offset', { offset_ms: Math.max(-5000, Math.min(5000, v)) });

  return (
    <>
      <div className="group-title">Lyrics timing</div>
      <div className="group">
        <div className="row-item">
          <Tile color="#ff9f0a"><Icon name="clock" size={18} /></Tile>
          <div className="grow"><div>Sync offset</div><div className="sub">For this song · positive = earlier</div></div>
          <span className="value">{off > 0 ? '+' : ''}{off} ms</span>
        </div>
        <div className="row-item">
          <div className="grow sub">Fine</div>
          <div className="stepper"><button onClick={() => setOff(off - 10)}>−</button><i /><button onClick={() => setOff(off + 10)}>+</button></div>
          <div className="grow sub right">Coarse</div>
          <div className="stepper"><button onClick={() => setOff(off - 100)}>−</button><i /><button onClick={() => setOff(off + 100)}>+</button></div>
        </div>
        <div className="row-item"><input className="ios-range" type="range" min="-2000" max="2000" step="10" value={off} onChange={(e) => setOff(+e.target.value)} /></div>
        <button className="row-item link" onClick={() => setOff(0)}>Reset to 0</button>
      </div>

      <div className="group-title">Display</div>
      <div className="group">
        <div className="row-item">
          <Tile color="#bf5af2"><Icon name="wave" size={18} /></Tile>
          <div className="grow">Karaoke sweep</div>
          <Switch checked={st.sweep} onChange={st.setSweep} />
        </div>
        <div className="row-item">
          <Tile color="#0a84ff"><span className="aa">Aa</span></Tile>
          <input className="ios-range" type="range" min="0.7" max="1.6" step="0.05" value={st.fontScale} onChange={(e) => st.setFontScale(+e.target.value)} />
        </div>
      </div>

      {window.electronAPI?.openKeysFile && (
        <>
          <div className="group-title">AI and accounts</div>
          <div className="group">
            <button className="row-item" onClick={() => window.electronAPI.openKeysFile()}>
              <Tile color="#ff375f"><Icon name="sparkle" size={18} /></Tile>
              <div className="grow"><div>API keys</div><div className="sub">Opens the settings file. Save it, then restart.</div></div>
            </button>
            <button className="row-item link" onClick={() => window.electronAPI.restart()}>Restart LiveLyrics</button>
          </div>
        </>
      )}

      <div className="group-title">Translation</div>
      <div className="group">
        <div className="row-item">
          <Tile color="#30d158"><Icon name="globe" size={18} /></Tile>
          <div className="grow">Show translation</div>
          <Switch checked={st.translateOn} onChange={st.setTranslateOn} />
        </div>
        <label className="row-item pick">
          <div className="grow">Language</div>
          <select value={st.targetLang} onChange={(e) => st.setTargetLang(e.target.value)}>
            {Object.entries(langs).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </div>
    </>
  );
}

// ───────────────── Sheet shell (iOS material, swipe down to dismiss) ─────────────────
const TITLES = { search: 'Search', history: 'History', settings: 'Settings' };

export default function Drawer() {
  const drawer = useStore((s) => s.drawer);
  const setDrawer = useStore((s) => s.setDrawer);
  const sheet = useRef(null);
  const close = () => setDrawer(null);

  useEffect(() => {
    if (!drawer) return;
    const onKey = (e) => { if (e.key === 'Escape') close(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drawer]);

  // swipe the grabber / header down to dismiss (bottom-sheet layout)
  const drag = (e) => {
    if (e.target.closest('button')) return;
    const el = sheet.current; let y0 = e.clientY, dy = 0;
    const move = (ev) => { dy = Math.max(0, ev.clientY - y0); el.style.transition = 'none'; el.style.transform = `translateY(${dy}px)`; };
    const up = () => {
      window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up);
      el.style.transition = ''; if (dy > 90) close(); else el.style.transform = '';
    };
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
  };

  if (!drawer) return null;
  return (
    <>
      <div className="scrim" onClick={close} />
      <aside className="ios-sheet" ref={sheet} role="dialog" aria-label={TITLES[drawer]}>
        <div className="sheet-head" onPointerDown={drag}>
          <div className="grab" />
          <h2>{TITLES[drawer]}</h2>
          <button className="done" onClick={close}>Done</button>
        </div>
        <div className="sheet-body">
          {drawer === 'search' && <Search close={close} />}
          {drawer === 'history' && <History close={close} />}
          {drawer === 'settings' && <Settings />}
        </div>
      </aside>
    </>
  );
}
