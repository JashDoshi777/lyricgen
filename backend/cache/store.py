"""
SQLite cache (stdlib, zero setup, instant). Replaces the old ChromaDB key-value use.
Stores lyrics, AI explanations, translations and play history.
"""

import json
import os
import re
import sqlite3
import threading
import time

from config import Config


def song_key(title, artist):
    norm = lambda s: re.sub(r'[^\w]+', ' ', (s or '').lower()).strip()
    return f"{norm(title)}|{norm(artist)}"


class Cache:
    def __init__(self, path=None):
        self.path = path or Config.DB_PATH
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.executescript('''
            CREATE TABLE IF NOT EXISTS kv (ns TEXT, k TEXT, v TEXT, ts REAL, PRIMARY KEY (ns, k));
            CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, artist TEXT, album TEXT, artwork TEXT, played_at REAL);
        ''')
        self._db.commit()

    def _get(self, ns, k):
        with self._lock:
            row = self._db.execute('SELECT v FROM kv WHERE ns=? AND k=?', (ns, k)).fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except Exception:
            return None

    def _set(self, ns, k, v):
        with self._lock:
            self._db.execute('INSERT OR REPLACE INTO kv VALUES (?,?,?,?)', (ns, k, json.dumps(v), time.time()))
            self._db.commit()

    # Lyrics are keyed by song + rounded duration so different edits don't collide.
    @staticmethod
    def _lkey(title, artist, duration):
        return song_key(title, artist) + (f"|{int(round(duration / 3))}" if duration else '')

    def get_lyrics(self, title, artist, duration=None):
        return self._get('lyrics', self._lkey(title, artist, duration))

    def set_lyrics(self, title, artist, data, duration=None):
        if data and data.get('lines'):
            self._set('lyrics', self._lkey(title, artist, duration), data)

    def get_explanation(self, title, artist, line):
        return self._get('explain', f"{song_key(title, artist)}|{line}")

    def set_explanation(self, title, artist, line, value):
        self._set('explain', f"{song_key(title, artist)}|{line}", value)

    def get_translation(self, text, lang):
        return self._get('translate', f"{lang}|{text}")

    def set_translation(self, text, lang, value):
        self._set('translate', f"{lang}|{text}", value)

    def add_to_history(self, title, artist, album='', artwork=''):
        with self._lock:
            last = self._db.execute('SELECT title, artist FROM history ORDER BY id DESC LIMIT 1').fetchone()
            if last and last == (title, artist):
                return
            self._db.execute('INSERT INTO history (title, artist, album, artwork, played_at) VALUES (?,?,?,?,?)',
                             (title, artist, album, artwork, time.time()))
            self._db.commit()

    def set_history_artwork(self, title, artist, artwork):
        with self._lock:
            self._db.execute('UPDATE history SET artwork=? WHERE title=? AND artist=? AND (artwork IS NULL OR artwork="")',
                             (artwork, title, artist))
            self._db.commit()

    def get_history(self, limit=50):
        with self._lock:
            rows = self._db.execute(
                'SELECT title, artist, album, artwork, played_at FROM history ORDER BY id DESC LIMIT ?',
                (limit,)).fetchall()
        return [dict(zip(('title', 'artist', 'album', 'artwork', 'played_at'), r)) for r in rows]

    def clear_history(self):
        with self._lock:
            self._db.execute('DELETE FROM history')
            self._db.commit()


_instance = None


def get_cache():
    global _instance
    if _instance is None:
        _instance = Cache()
    return _instance
