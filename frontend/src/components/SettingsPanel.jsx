import { useState } from 'react';
import { motion } from 'framer-motion';
import useStore from '../hooks/useStore';

const BACKEND_URL = 'http://localhost:5000';

export default function SettingsPanel() {
    const {
        displayMode,
        setDisplayMode,
        translationEnabled,
        toggleTranslation,
        targetLanguage,
        setTargetLanguage,
        theme,
        toggleTheme,
    } = useStore();

    const [searchTitle, setSearchTitle] = useState('');
    const [searchArtist, setSearchArtist] = useState('');
    const [searching, setSearching] = useState(false);

    const handleManualSearch = async () => {
        if (!searchTitle.trim()) return;
        setSearching(true);
        try {
            await fetch(`${BACKEND_URL}/api/search?title=${encodeURIComponent(searchTitle)}&artist=${encodeURIComponent(searchArtist)}`);
        } catch (e) { /* ignore */ }
        setSearching(false);
        setSearchTitle('');
        setSearchArtist('');
    };

    return (
        <div className="flex-1 mx-4 mt-4">
            <div className="glass p-6 space-y-6" style={{ borderRadius: 'var(--radius-lg, 24px)', maxHeight: 'calc(100vh - 240px)', overflow: 'auto' }}>
                <h2 className="font-display font-bold text-xl text-[var(--text-primary)]">Settings</h2>

                {/* Manual Search */}
                <Section title="Manual Song Search" icon="🔍">
                    <div className="space-y-2">
                        <input
                            type="text"
                            placeholder="Song title"
                            value={searchTitle}
                            onChange={(e) => setSearchTitle(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)]
                text-[var(--text-primary)] text-sm placeholder:text-[var(--text-muted)]
                focus:outline-none focus:ring-2 focus:ring-accent-500/30 transition-all"
                        />
                        <input
                            type="text"
                            placeholder="Artist (optional)"
                            value={searchArtist}
                            onChange={(e) => setSearchArtist(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)]
                text-[var(--text-primary)] text-sm placeholder:text-[var(--text-muted)]
                focus:outline-none focus:ring-2 focus:ring-accent-500/30 transition-all"
                        />
                        <button
                            onClick={handleManualSearch}
                            disabled={searching || !searchTitle.trim()}
                            className="w-full py-2.5 rounded-xl bg-accent-500 text-white text-sm font-semibold
                hover:bg-accent-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all
                shadow-md hover:shadow-lg"
                        >
                            {searching ? 'Searching...' : 'Search & Load Lyrics'}
                        </button>
                    </div>
                </Section>

                {/* Display Mode */}
                <Section title="Lyric Display Mode" icon="🎤">
                    <div className="grid grid-cols-2 gap-2">
                        {[
                            { id: 'spotify', label: 'Spotify', desc: 'Centered scroll' },
                            { id: 'karaoke', label: 'Karaoke', desc: 'Word highlight' },
                        ].map((mode) => (
                            <button
                                key={mode.id}
                                onClick={() => setDisplayMode(mode.id)}
                                className={`p-3 rounded-xl text-left transition-all border ${displayMode === mode.id
                                        ? 'bg-accent-500/10 border-accent-500/30 text-accent-500'
                                        : 'bg-[var(--bg-primary)] border-[var(--border-color)] text-[var(--text-secondary)]'
                                    }`}
                            >
                                <p className="text-sm font-semibold">{mode.label}</p>
                                <p className="text-xs opacity-60">{mode.desc}</p>
                            </button>
                        ))}
                    </div>
                </Section>

                {/* Theme */}
                <Section title="Theme" icon="🎨">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-[var(--text-secondary)]">
                            {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}
                        </span>
                        <button onClick={toggleTheme} className="theme-toggle" />
                    </div>
                </Section>

                {/* Translation */}
                <Section title="Translation" icon="🌐">
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-[var(--text-secondary)]">Enable Translation</span>
                            <button
                                onClick={toggleTranslation}
                                className={`w-12 h-6 rounded-full relative transition-colors ${translationEnabled ? 'bg-accent-500' : 'bg-[var(--border-color)]'
                                    }`}
                            >
                                <div
                                    className={`w-5 h-5 rounded-full bg-white absolute top-0.5 transition-transform
                    shadow-sm ${translationEnabled ? 'translate-x-6' : 'translate-x-0.5'}`}
                                />
                            </button>
                        </div>
                        {translationEnabled && (
                            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
                                <select
                                    value={targetLanguage}
                                    onChange={(e) => setTargetLanguage(e.target.value)}
                                    className="w-full px-4 py-2.5 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)]
                    text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-accent-500/30"
                                >
                                    <option value="en">English</option>
                                    <option value="es">Spanish</option>
                                    <option value="fr">French</option>
                                    <option value="de">German</option>
                                    <option value="ja">Japanese</option>
                                    <option value="ko">Korean</option>
                                    <option value="zh">Chinese</option>
                                    <option value="hi">Hindi</option>
                                    <option value="pt">Portuguese</option>
                                    <option value="ru">Russian</option>
                                    <option value="ar">Arabic</option>
                                    <option value="it">Italian</option>
                                </select>
                            </motion.div>
                        )}
                    </div>
                </Section>
            </div>
        </div>
    );
}

function Section({ title, icon, children }) {
    return (
        <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                <span>{icon}</span>
                {title}
            </h3>
            {children}
        </div>
    );
}
