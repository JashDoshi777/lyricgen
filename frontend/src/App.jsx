import { useEffect } from 'react';
import useStore from './hooks/useStore';
import useSocket from './hooks/useSocket';
import Header from './components/Header';
import NowPlaying from './components/NowPlaying';
import LyricsPanel from './components/LyricsPanel';
import HistoryPanel from './components/HistoryPanel';
import SettingsPanel from './components/SettingsPanel';
import './index.css';

export default function App() {
  const { theme, activePanel } = useStore();

  // Initialize theme
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  // Connect to backend
  useSocket();

  return (
    <div className="min-h-screen bg-gradient-mesh relative">
      {/* Background glow orbs */}
      <div
        className="glow-orb"
        style={{
          top: '10%',
          left: '15%',
          background: 'radial-gradient(circle, rgba(99, 102, 241, 0.3), transparent)',
        }}
      />
      <div
        className="glow-orb"
        style={{
          bottom: '20%',
          right: '10%',
          background: 'radial-gradient(circle, rgba(168, 85, 247, 0.2), transparent)',
        }}
      />

      {/* App shell */}
      <div className="relative z-10 flex flex-col h-screen">
        <Header />
        <NowPlaying />

        {/* Main content area */}
        <div className="flex-1 overflow-hidden flex flex-col pb-4">
          {activePanel === 'lyrics' && <LyricsPanel />}
          {activePanel === 'history' && <HistoryPanel />}
          {activePanel === 'settings' && <SettingsPanel />}
        </div>
      </div>
    </div>
  );
}
