import { memo, useEffect, useLayoutEffect, useRef, useCallback, useState } from 'react';
import useStore from '../store';
import { clock } from '../lib/clock';
import { post } from '../lib/api';
import { Icon } from './Icons';

const LOOKAHEAD = 0.12; // show a line a hair early; compensates render + eye latency

function findIndex(lines, t) {
  let lo = 0, hi = lines.length - 1, r = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (lines[mid].time <= t) { r = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return r;
}

const Line = memo(function Line({ i, text, sub, dist, active, onSeek, onExplain, canSeek }) {
  return (
    <div
      className={`ln${active ? ' on' : ''}`}
      data-d={dist}
      data-i={i}
      onClick={canSeek ? () => onSeek(i) : undefined}
      style={{ cursor: canSeek ? 'pointer' : 'default' }}
    >
      <span className="ln-text">{text}</span>
      {sub && <span className="ln-sub">{sub}</span>}
      <button className="ln-ai" title="What does this mean?" onClick={(e) => { e.stopPropagation(); onExplain(i); }}><Icon name="sparkle" size={16} /></button>
    </div>
  );
});

export default function LyricsView() {
  const lines = useStore((s) => s.lyrics.lines);
  const synced = useStore((s) => s.lyrics.synced);
  const status = useStore((s) => s.lyrics.status);
  const song = useStore((s) => s.song);
  const active = useStore((s) => s.activeIndex);
  const sweep = useStore((s) => s.sweep);
  const translateOn = useStore((s) => s.translateOn);
  const lang = useStore((s) => s.targetLang);
  const trans = useStore((s) => s.translations[`${s.song?.id}:${s.targetLang}`]);

  const viewRef = useRef(null);
  const trackRef = useRef(null);
  const offsetRef = useRef(0);
  const jumpRef = useRef(false);
  const yRef = useRef(0);
  const browsingRef = useRef(false);
  const glideRef = useRef(null);
  const [browsing, setBrowsing] = useState(false);
  const offsetMs = song?.offset_ms || 0;
  useEffect(() => { offsetRef.current = offsetMs / 1000; }, [offsetMs]);

  // ── tick: find active line (React only re-renders when it changes) + sweep progress
  useEffect(() => {
    if (!synced || !lines.length) return;
    // Use the window that hosts us (Picture-in-Picture or main). rAF only runs while playing and
    // visible; otherwise a slow timer keeps things correct at ~zero cost.
    const win = viewRef.current?.ownerDocument?.defaultView || window;
    const doc = win.document;
    let raf = 0, timer = 0, last = -2, lastP = -1, el = null, jumpTimer = 0;
    const tick = () => {
      const t = clock.position() + offsetRef.current + LOOKAHEAD;
      const idx = findIndex(lines, t);
      if (idx !== last) {
        // Big jump (seek, or coming back to a tab): skip the animation instead of scrolling through it
        if (last !== -2 && Math.abs(idx - last) > 3 && viewRef.current) {
          jumpRef.current = true;
          viewRef.current.classList.add('jump');
          win.clearTimeout(jumpTimer);
          jumpTimer = win.setTimeout(() => viewRef.current?.classList.remove('jump'), 150);
        }
        last = idx; lastP = -1;
        useStore.getState().setActiveIndex(idx);
      }
      if (idx < 0) return;
      if (!el || !el.isConnected || !el.classList.contains('on')) el = trackRef.current?.querySelector('.ln.on') || null;
      if (el) {
        const start = lines[idx].time;
        const end = idx + 1 < lines.length ? lines[idx + 1].time : start + 5;
        const dur = Math.max(0.6, Math.min(end - start, 8) * 0.9);   // finish just before the next line
        const p = Math.max(0, Math.min(1, (t - LOOKAHEAD - start) / dur));
        if (Math.abs(p - lastP) >= 0.004) { lastP = p; el.style.setProperty('--p', p.toFixed(3)); }
      }
    };
    const loop = () => {
      tick();
      if (clock.playing && !doc.hidden) raf = win.requestAnimationFrame(loop);
      else timer = win.setTimeout(loop, doc.hidden ? 200 : 300);
    };
    loop();
    return () => { win.cancelAnimationFrame(raf); win.clearTimeout(timer); win.clearTimeout(jumpTimer); };
  }, [lines, synced]);

  // ── glide: translate the track so the active line sits ~38% down the view
  const glide = useCallback((instant) => {
    const view = viewRef.current, track = trackRef.current;
    if (!view || !track || !synced) return;
    const el = track.querySelector(`.ln[data-i="${Math.max(active, 0)}"]`);
    if (!el) return;
    const target = el.offsetTop + el.offsetHeight / 2;
    const anchor = parseFloat(getComputedStyle(view).getPropertyValue('--anchor')) || 0.38;
    const y = view.clientHeight * anchor - target;
    yRef.current = y;
    if (browsingRef.current) return;     // user is scrolling: don't fight them
    if (jumpRef.current) { instant = true; jumpRef.current = false; }
    track.style.transition = instant ? 'none' : '';
    track.style.transform = `translate3d(0, ${y}px, 0)`;
    if (instant) { void track.offsetHeight; track.style.transition = ''; }
  }, [active, synced]);

  useLayoutEffect(() => { glideRef.current = glide; glide(false); }, [glide, trans, translateOn]);

  // ── manual scrolling (wheel / touch): browse freely, glide back to the current line after a pause
  useEffect(() => {
    const view = viewRef.current;
    if (!view || !synced) return;
    let timer = 0, touchY = null;
    const resume = () => {
      browsingRef.current = false;
      setBrowsing(false);
      const t = trackRef.current;
      if (t) t.style.transition = '';
      glideRef.current?.(false);
    };
    const scrollBy = (dy) => {
      const track = trackRef.current;
      if (!track || !track.firstElementChild) return;
      const lns = track.querySelectorAll('.ln');
      if (!lns.length) return;
      const anchor = parseFloat(getComputedStyle(view).getPropertyValue('--anchor')) || 0.38;
      const H = view.clientHeight, first = lns[0], last = lns[lns.length - 1];
      const maxY = H * anchor - (first.offsetTop + first.offsetHeight / 2);
      const minY = H * 0.75 - (last.offsetTop + last.offsetHeight / 2);
      if (!browsingRef.current) { browsingRef.current = true; setBrowsing(true); }
      yRef.current = Math.max(Math.min(minY, maxY), Math.min(maxY, yRef.current - dy));
      track.style.transition = 'transform .12s ease-out';
      track.style.transform = `translate3d(0, ${yRef.current}px, 0)`;
      window.clearTimeout(timer);
      timer = window.setTimeout(resume, 3500);
    };
    const onWheel = (e) => { e.preventDefault(); scrollBy(e.deltaMode === 1 ? e.deltaY * 32 : e.deltaY); };
    const onTouchStart = (e) => { touchY = e.touches[0].clientY; };
    const onTouchMove = (e) => {
      if (touchY == null) return;
      e.preventDefault();
      const y = e.touches[0].clientY; scrollBy(touchY - y); touchY = y;
    };
    view.addEventListener('wheel', onWheel, { passive: false });
    view.addEventListener('touchstart', onTouchStart, { passive: true });
    view.addEventListener('touchmove', onTouchMove, { passive: false });
    view.__resume = resume;
    return () => {
      window.clearTimeout(timer);
      view.removeEventListener('wheel', onWheel);
      view.removeEventListener('touchstart', onTouchStart);
      view.removeEventListener('touchmove', onTouchMove);
      browsingRef.current = false;
    };
  }, [synced, lines]);
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const RO = view.ownerDocument.defaultView.ResizeObserver || ResizeObserver;
    const ro = new RO(() => glide(true));
    ro.observe(view);
    return () => ro.disconnect();
  }, [glide]);

  const onSeek = useCallback((i) => {
    const l = useStore.getState().lyrics.lines[i];
    const off = (useStore.getState().song?.offset_ms || 0) / 1000;
    post('/api/seek', { position_sec: Math.max(0, l.time - off) });
  }, []);

  const onExplain = useCallback(async (i) => {
    const st = useStore.getState();
    const ls = st.lyrics.lines;
    st.setExplain({ line: ls[i].text, loading: true, data: null });
    try {
      const data = await post('/api/explain', {
        line: ls[i].text, title: st.song?.title, artist: st.song?.artist,
        context: ls.slice(Math.max(0, i - 3), i + 4).map((l) => l.text),
      });
      useStore.getState().setExplain({ line: ls[i].text, loading: false, data });
    } catch {
      useStore.getState().setExplain({ line: ls[i].text, loading: false, data: { meaning: 'Could not reach the backend.', emotion: '', explanation: '' } });
    }
  }, []);

  // ── translations (fetched once per song+language, cached server-side)
  useEffect(() => {
    if (!translateOn || !song || !lines.length || trans) return;
    const key = `${song.id}:${lang}`;
    post('/api/translate', { lines: lines.map((l) => ({ time: l.time, text: l.text })), target_lang: lang })
      .then((d) => useStore.getState().setTranslations(key, (d.lines || []).map((l) => l.translation)))
      .catch(() => {});
  }, [translateOn, lang, song, lines, trans]);

  if (!song) return null;
  if (status === 'loading') return <div className="lv-msg"><div className="spinner" /><p>Finding lyrics…</p></div>;
  if (!lines.length) return <div className="lv-msg"><p className="big">No lyrics found</p><p>Try the search (top right) with a cleaner title.</p></div>;

  // Plain, un-timed lyrics: static scrollable text
  if (!synced) {
    return (
      <div className="lv plain" ref={viewRef}>
        <p className="plain-note">These lyrics aren’t time-synced</p>
        {lines.map((l, i) => <div key={i} className="ln on" style={{ '--p': 1 }}><span className="ln-text">{l.text}</span></div>)}
      </div>
    );
  }

  return (
    <div className={`lv${sweep ? ' sweep' : ''}${browsing ? ' browse' : ''}`} ref={viewRef}>
      {browsing && <button className="lv-now" onClick={() => viewRef.current?.__resume?.()}><Icon name="arrowdown" size={14} /> Current line</button>}
      <div className="lv-track" ref={trackRef}>
        {active < 0 && <div className="interlude"><i /><i /><i /></div>}
        {lines.map((l, i) => {
          const d = i - active;
          return (
            <Line key={i} i={i} text={l.text}
              sub={translateOn ? trans?.[i] : null}
              dist={Math.min(Math.abs(d), 6) * (d < 0 ? -1 : 1)}
              active={d === 0} canSeek onSeek={onSeek} onExplain={onExplain} />
          );
        })}
        <div style={{ height: '60vh' }} />
      </div>
    </div>
  );
}
