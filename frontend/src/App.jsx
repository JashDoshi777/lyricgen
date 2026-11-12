import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import useStore from './store';
import useBackend from './useBackend';
import Background from './components/Background';
import PlayerBar from './components/PlayerBar';
import LyricsView from './components/LyricsView';
import Drawer from './components/Drawer';
import ExplainSheet from './components/ExplainSheet';
import Widget from './components/Widget';
import { Icon } from './components/Icons';
import { post } from './lib/api';

const isWidget = new URLSearchParams(location.search).has('widget');
const canPip = typeof window !== 'undefined' && 'documentPictureInPicture' in window;

// Give the floating window the app's CSS. Linked stylesheets are loaded by URL (byte-identical, so
// things like `background-clip: text` survive); only inline <style> falls back to copying rules.
function copyStyles(target) {
  const loads = [];
  for (const sheet of document.styleSheets) {
    if (sheet.href) {
      const link = target.document.createElement('link');
      link.rel = 'stylesheet';
      link.href = sheet.href;
      loads.push(new Promise((res) => { link.onload = link.onerror = res; }));
      target.document.head.appendChild(link);
    } else {
      try {
        const style = target.document.createElement('style');
        style.textContent = [...sheet.cssRules].map((r) => r.cssText).join('\n');
        target.document.head.appendChild(style);
      } catch { /* ignore */ }
    }
  }
  return Promise.race([Promise.all(loads), new Promise((res) => setTimeout(res, 2000))]);
}

export default function App() {
  useBackend();
  const connected = useStore((s) => s.connected);
  const fontScale = useStore((s) => s.fontScale);
  const setDrawer = useStore((s) => s.setDrawer);
  const [pip, setPip] = useState(null);
  const [toast, setToast] = useState('');

  useEffect(() => {
    document.documentElement.style.setProperty('--fs', fontScale);
    document.documentElement.classList.toggle('widget-mode', isWidget);
    if (window.electronAPI) document.documentElement.classList.add('desktop', `plat-${window.electronAPI.platform}`);
  }, [fontScale]);

  const say = (m) => { setToast(m); setTimeout(() => setToast(''), 4000); };

  const popOut = async () => {
    if (pip) { pip.close(); return; }
    try {
      const w = await window.documentPictureInPicture.requestWindow({ width: 440, height: 240 });
      await copyStyles(w);
      w.document.documentElement.classList.add('widget-mode');
      w.document.body.style.cssText = 'margin:0;background:#050507;color:#fff;overflow:hidden';
      w.addEventListener('pagehide', () => setPip(null));
      setPip(w);
    } catch { say('Could not open the floating window.'); }
  };

  const desktopWidget = async () => {
    if (window.electronAPI?.openWidget) { window.electronAPI.openWidget(); return; }   // packaged desktop app
    try {
      const r = await post('/api/widget/launch');
      say(r.message || (r.ok ? 'Desktop widget opening…' : 'Could not start the desktop widget.'));
    } catch { say('Backend not reachable.'); }
  };

  if (isWidget) return <><Widget /><ExplainSheet /></>;

  return (
    <div className="app">
      <Background />
      <header className="top">
        <div className="brand"><img src="/icon.png" alt="" width="26" height="26" /> LiveLyrics</div>
        <div className="top-actions">
          {!connected && <span className="chip warn">backend offline</span>}
          {canPip && <button className={pip ? 'on' : ''} onClick={popOut} title="Pop out a floating lyrics window (stays on top of every app)"><Icon name="pip" /></button>}
          <button onClick={desktopWidget} title="Open the desktop widget"><Icon name="monitor" /></button>
          <button onClick={() => setDrawer('search')} title="Search"><Icon name="search" /></button>
          <button onClick={() => setDrawer('history')} title="History"><Icon name="history" /></button>
          <button onClick={() => setDrawer('settings')} title="Settings"><Icon name="settings" /></button>
        </div>
      </header>
      <main className="stage">
        <PlayerBar />
        <section className="lyrics"><LyricsView /><Empty /></section>
      </main>
      <Drawer />
      <ExplainSheet />
      {toast && <div className="toast">{toast}</div>}
      {pip && createPortal(<><Widget onClose={() => pip.close()} /><ExplainSheet /></>, pip.document.body)}
    </div>
  );
}

function Empty() {
  const song = useStore((s) => s.song);
  if (song) return null;
  return (
    <div className="lv-msg">
      <div className="eq"><i /><i /><i /><i /><i /></div>
      <p className="big">Play a song</p>
      <p>Lyrics appear automatically from Spotify, Apple Music, YouTube and more.</p>
    </div>
  );
}
