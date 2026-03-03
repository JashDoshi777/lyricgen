import { create } from 'zustand';

const useStore = create((set, get) => ({
    // ── Current Song ─────────────────────────────────
    currentSong: null,
    setCurrentSong: (song) => set({ currentSong: song }),

    // ── Lyrics ───────────────────────────────────────
    lyrics: [],
    synced: false,
    lineDurations: [],  // pre-computed ms duration for each line
    currentLineIndex: -1,
    currentLineDuration: 3000,
    previousLines: [],
    nextLines: [],
    setLyrics: (newLyrics, synced = false, durations = []) => {
        const current = get().lyrics;
        // Only reset line index when lyrics actually change (new song).
        // Re-emits of the same lyrics (e.g. on reconnect) should NOT reset the index.
        const isNewSong =
            current.length !== newLyrics.length ||
            (current.length > 0 && newLyrics.length > 0 && current[0]?.text !== newLyrics[0]?.text);
        set({
            lyrics: newLyrics,
            synced,
            lineDurations: durations,
            ...(isNewSong ? { currentLineIndex: -1 } : {}),
        });
    },
    setCurrentLine: (index, previous = [], next = [], duration = 3000) =>
        set({ currentLineIndex: index, currentLineDuration: duration, previousLines: previous, nextLines: next }),

    // ── Theme ────────────────────────────────────────
    theme: localStorage.getItem('lyrics-theme') || 'dark',
    toggleTheme: () => {
        const newTheme = get().theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('lyrics-theme', newTheme);
        document.documentElement.classList.toggle('dark', newTheme === 'dark');
        set({ theme: newTheme });
    },

    // ── Display Mode ─────────────────────────────────
    displayMode: localStorage.getItem('lyrics-display-mode') || 'spotify',
    setDisplayMode: (mode) => {
        localStorage.setItem('lyrics-display-mode', mode);
        set({ displayMode: mode });
    },

    // ── Explanation ──────────────────────────────────
    explanation: null,
    explanationLoading: false,
    showExplanation: false,
    setExplanation: (explanation) => set({ explanation, explanationLoading: false, showExplanation: true }),
    setExplanationLoading: (loading) => set({ explanationLoading: loading }),
    closeExplanation: () => set({ showExplanation: false }),

    // ── Translation ──────────────────────────────────
    translationEnabled: false,
    targetLanguage: 'en',
    translations: {},
    toggleTranslation: () => set((s) => ({ translationEnabled: !s.translationEnabled })),
    setTargetLanguage: (lang) => set({ targetLanguage: lang }),
    setTranslations: (translations) => set({ translations }),

    // ── History ──────────────────────────────────────
    history: [],
    setHistory: (history) => set({ history }),

    // ── Connection ───────────────────────────────────
    connected: false,
    setConnected: (connected) => set({ connected }),

    // ── Playback ─────────────────────────────────────
    isPlaying: true,
    setIsPlaying: (playing) => set({ isPlaying: playing }),

    // ── UI State ─────────────────────────────────────
    activePanel: 'lyrics', // 'lyrics' | 'history' | 'settings'
    setActivePanel: (panel) => set({ activePanel: panel }),
}));

export default useStore;
