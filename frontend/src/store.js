import { create } from 'zustand';

const load = (k, d) => { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } };
const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } };

const useStore = create((set, get) => ({
  connected: false,
  song: null,
  lyrics: { status: 'idle', lines: [], synced: false, source: '' },
  playing: false,
  positionKnown: true,
  activeIndex: -1,

  setConnected: (connected) => set({ connected }),
  setSong: (song) => set({ song }),
  setLyrics: (l) => set({ lyrics: l, activeIndex: -1 }),
  setPlayback: (p) => set({ playing: p.playing, positionKnown: p.position_known }),
  setActiveIndex: (i) => set({ activeIndex: i }),

  // settings (persisted)
  sweep: load('ll.sweep', true),
  fontScale: load('ll.fontScale', 1),
  translateOn: load('ll.translateOn', false),
  targetLang: load('ll.lang', 'en'),
  setSweep: (v) => { save('ll.sweep', v); set({ sweep: v }); },
  setFontScale: (v) => { v = Math.max(0.7, Math.min(1.6, v)); save('ll.fontScale', v); set({ fontScale: v }); },
  setTranslateOn: (v) => { save('ll.translateOn', v); set({ translateOn: v }); },
  setTargetLang: (v) => { save('ll.lang', v); set({ targetLang: v }); },

  translations: {},               // `${songId}:${lang}` -> string[]
  setTranslations: (key, arr) => set({ translations: { ...get().translations, [key]: arr } }),

  drawer: null,                   // null | 'search' | 'history' | 'settings'
  setDrawer: (d) => set({ drawer: d }),
  explain: null,                  // {line, loading, data}
  setExplain: (e) => set({ explain: e }),
}));

export default useStore;
