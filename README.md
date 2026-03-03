# 🎵 LiveLyrics — Real-Time Lyrics Overlay

A production-quality system that detects the currently playing song from **any app**, fetches synchronized lyrics, and displays them in real-time — with AI explanations, translation, and a floating desktop widget.

> Works with Spotify, YouTube, VLC, Apple Music, Chrome, Edge, and any app that plays audio.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Hybrid Detection** | Windows SMTC metadata + AcoustID audio fingerprinting |
| **Synced Lyrics** | Real-time lyric scrolling via LRCLib → Genius → Musixmatch |
| **Spotify Mode** | Centered active line with faded surrounding lines |
| **Karaoke Mode** | Word-level highlighting with animated sweep |
| **AI Explanations** | Click any lyric for meaning/emotion via Groq (llama3-70b) |
| **Translation** | Real-time lyric translation to 12 languages |
| **Floating Widget** | Always-on-top Electron overlay with compact/expanded modes |
| **Dark / Light Mode** | Apple-style theme switching with smooth transitions |
| **Caching** | ChromaDB caches lyrics, explanations, translations, and history |

---

## 🏗 Architecture

```
Music (any app)  →  Detection Layer (SMTC / AcoustID)
                           ↓
                    Song Identified
                           ↓
                  Lyrics Pipeline (LRCLib → Genius → Musixmatch)
                           ↓
                    ChromaDB Cache
                           ↓
                  Flask + WebSocket Server
                      ↓           ↓
              React Web App    Electron Widget
                      ↓
            AI Explanation (Groq)
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Windows 10/11** (required for SMTC + WASAPI)
- **fpcalc.exe** in the project root (from [Chromaprint](https://acoustid.org/chromaprint))

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Edit `backend/.env` with your API keys:

```env
ACOUSTID_API_KEY=your_key
GROQ_API_KEY=your_key
GENIUS_ACCESS_TOKEN=your_token   # optional
```

Start the backend:

```bash
python app.py
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

### 3. Floating Widget (Optional)

```bash
cd electron
npm install
npm start
```

---

## 📁 Project Structure

```
live-lyrics-app/
├── backend/
│   ├── app.py                  # Flask + SocketIO server
│   ├── config.py               # Environment config
│   ├── audio_capture/          # WASAPI loopback capture
│   ├── recognition/            # SMTC + AcoustID detection
│   ├── lyrics/                 # LRCLib / Genius / Musixmatch
│   ├── groq_explain/           # AI lyric explanation
│   ├── translation/            # MyMemory translation
│   ├── cache/                  # ChromaDB caching
│   └── websocket/              # Event bus + sync engine
├── frontend/
│   └── src/
│       ├── components/         # React UI components
│       ├── hooks/              # Zustand store + Socket.IO hook
│       └── App.jsx             # Root app
├── electron/
│   ├── main.js                 # Electron shell
│   ├── preload.js              # IPC bridge
│   └── widget.html             # Floating widget UI
└── README.md
```

---

## 🔑 API Keys

| Service | Purpose | Link |
|---------|---------|------|
| AcoustID | Audio fingerprint recognition | [acoustid.org](https://acoustid.org/) |
| Groq | AI lyric explanations | [console.groq.com](https://console.groq.com/) |
| Genius | Fallback lyrics (optional) | [genius.com/api-clients](https://genius.com/api-clients) |

---

## 🛠 Tech Stack

**Backend:** Flask, Flask-SocketIO, sounddevice, pyacoustid, ChromaDB, Groq SDK  
**Frontend:** React 18, Vite, TailwindCSS, Framer Motion, Zustand, Socket.IO  
**Widget:** Electron (frameless, always-on-top, transparent)

---

## 📄 License

MIT
