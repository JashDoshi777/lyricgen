import { useEffect } from 'react';
import useStore from '../store';
import { Icon } from './Icons';

export default function ExplainSheet() {
  const ex = useStore((s) => s.explain);
  const set = useStore((s) => s.setExplain);

  useEffect(() => {
    if (!ex) return;
    const onKey = (e) => { if (e.key === 'Escape') set(null); };
    // Listen on every window we might live in (main page and the Picture-in-Picture window)
    const wins = new Set([window, ...[...document.querySelectorAll('.sheet')].map((n) => n.ownerDocument.defaultView)]);
    wins.forEach((w) => w.addEventListener('keydown', onKey));
    return () => wins.forEach((w) => w.removeEventListener('keydown', onKey));
  }, [ex, set]);

  if (!ex) return null;
  const d = ex.data;
  const failed = !ex.loading && (!d || d.emotion === 'Error' || /^Error/.test(d.meaning || ''));

  return (
    <>
      <div className="scrim" onClick={() => set(null)} />
      <div className="sheet xs" role="dialog" aria-label="Lyric insight">
        <div className="grab" />
        <header className="xs-head">
          <span className="xs-badge"><Icon name="sparkle" size={14} /> Lyric Insight</span>
          <button className="done" onClick={() => set(null)}>Done</button>
        </header>

        <blockquote className="xs-quote">“{ex.line}”</blockquote>

        {ex.loading && (
          <div className="xs-skel"><i style={{ width: '38%' }} /><i /><i /><i style={{ width: '72%' }} /></div>
        )}

        {failed && <p className="xs-error">Couldn’t get an explanation right now. Check your Groq key and model in <b>.env</b>, then try again.</p>}

        {!ex.loading && !failed && (
          <>
            {d.emotion && <span className="xs-emotion"><Icon name="sparkle" size={13} />{d.emotion}</span>}
            {d.meaning && <section><h4>Meaning</h4><p>{d.meaning}</p></section>}
            {d.explanation && <section><h4>In plain words</h4><p>{d.explanation}</p></section>}
          </>
        )}
      </div>
    </>
  );
}
