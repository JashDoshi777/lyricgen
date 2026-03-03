"""
ChromaDB caching layer.
Stores songs, lyrics, AI explanations, translations, and history.
Connects to ChromaDB Cloud using API key, tenant, and database.

Uses dummy embeddings since we only do ID-based lookups (no similarity search).
"""

import json
import time
import chromadb
from chromadb.config import Settings
from config import Config


# Dummy embedding function — returns a constant vector.
# We only use ChromaDB for ID-based key-value storage, not similarity search.
class _NoOpEmbeddingFunction:
    def __call__(self, input):
        # Return a single-element vector for each document
        return [[0.0] for _ in input]

    def name(self):
        return "default"


class LyricsCache:
    """ChromaDB Cloud-backed cache for all app data."""

    def __init__(self):
        self._ef = _NoOpEmbeddingFunction()

        if Config.CHROMA_API_KEY and Config.CHROMA_TENANT and Config.CHROMA_DATABASE:
            # Connect to ChromaDB Cloud
            self.client = chromadb.HttpClient(
                ssl=True,
                host='api.trychroma.com',
                port=8000,
                headers={
                    'x-chroma-token': Config.CHROMA_API_KEY,
                },
                tenant=Config.CHROMA_TENANT,
                database=Config.CHROMA_DATABASE,
                settings=Settings(
                    chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
                    chroma_client_auth_credentials=Config.CHROMA_API_KEY,
                    anonymized_telemetry=False,
                ),
            )
            print("[Cache] Connected to ChromaDB Cloud")
        else:
            # Fallback to local
            self.client = chromadb.PersistentClient(path='./chroma_db')
            print("[Cache] Using local ChromaDB (no cloud credentials)")
        self._init_collections()

    def _init_collections(self):
        """Initialize all ChromaDB collections."""
        self.lyrics_col = self.client.get_or_create_collection(
            name='lyrics',
            embedding_function=self._ef,
        )
        self.explanations_col = self.client.get_or_create_collection(
            name='explanations',
            embedding_function=self._ef,
        )
        self.translations_col = self.client.get_or_create_collection(
            name='translations',
            embedding_function=self._ef,
        )
        self.history_col = self.client.get_or_create_collection(
            name='history',
            embedding_function=self._ef,
        )

    @staticmethod
    def _song_key(title, artist):
        """Generate a unique key for a song."""
        return f"{title.lower().strip()}|||{artist.lower().strip()}"

    # ── Lyrics Cache ────────────────────────────────

    def get_lyrics(self, title, artist):
        """Get cached lyrics for a song."""
        key = self._song_key(title, artist)
        try:
            result = self.lyrics_col.get(ids=[key])
            if result and result['documents'] and result['documents'][0]:
                data = json.loads(result['documents'][0])
                return data
        except Exception:
            pass
        return None

    def set_lyrics(self, title, artist, lyrics_data):
        """Cache lyrics for a song."""
        key = self._song_key(title, artist)
        try:
            self.lyrics_col.upsert(
                ids=[key],
                documents=[json.dumps(lyrics_data)],
                metadatas=[{
                    'title': title,
                    'artist': artist,
                    'source': lyrics_data.get('source', 'unknown'),
                    'synced': str(lyrics_data.get('synced', False)),
                    'cached_at': str(time.time())
                }]
            )
        except Exception as e:
            print(f"[Cache] Error caching lyrics: {e}")

    # ── Explanation Cache ───────────────────────────

    def get_explanation(self, title, artist, lyric_line):
        """Get cached AI explanation for a lyric line."""
        key = f"{self._song_key(title, artist)}|||{lyric_line.strip().lower()}"
        try:
            result = self.explanations_col.get(ids=[key])
            if result and result['documents'] and result['documents'][0]:
                return json.loads(result['documents'][0])
        except Exception:
            pass
        return None

    def set_explanation(self, title, artist, lyric_line, explanation):
        """Cache an AI explanation."""
        key = f"{self._song_key(title, artist)}|||{lyric_line.strip().lower()}"
        try:
            self.explanations_col.upsert(
                ids=[key],
                documents=[json.dumps(explanation)],
                metadatas=[{
                    'title': title,
                    'artist': artist,
                    'line': lyric_line[:100],
                    'cached_at': str(time.time())
                }]
            )
        except Exception as e:
            print(f"[Cache] Error caching explanation: {e}")

    # ── Translation Cache ───────────────────────────

    def get_translation(self, text, target_lang):
        """Get cached translation."""
        key = f"{text.strip().lower()[:200]}|||{target_lang}"
        try:
            result = self.translations_col.get(ids=[key])
            if result and result['documents'] and result['documents'][0]:
                return result['documents'][0]
        except Exception:
            pass
        return None

    def set_translation(self, text, target_lang, translated):
        """Cache a translation."""
        key = f"{text.strip().lower()[:200]}|||{target_lang}"
        try:
            self.translations_col.upsert(
                ids=[key],
                documents=[translated],
                metadatas=[{
                    'source_text': text[:100],
                    'target_lang': target_lang,
                    'cached_at': str(time.time())
                }]
            )
        except Exception as e:
            print(f"[Cache] Error caching translation: {e}")

    # ── History ─────────────────────────────────────

    def add_to_history(self, title, artist, album=''):
        """Add a song to playback history."""
        key = f"history_{int(time.time() * 1000)}"
        try:
            self.history_col.add(
                ids=[key],
                documents=[json.dumps({
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'played_at': time.time()
                })],
                metadatas=[{
                    'title': title,
                    'artist': artist,
                    'played_at': str(time.time())
                }]
            )
        except Exception as e:
            print(f"[Cache] Error adding to history: {e}")

    def get_history(self, limit=50):
        """Get recent playback history."""
        try:
            result = self.history_col.get(
                limit=limit,
            )
            if result and result['documents']:
                history = [json.loads(doc) for doc in result['documents']]
                history.sort(key=lambda x: x.get('played_at', 0), reverse=True)
                return history[:limit]
        except Exception:
            pass
        return []


# Singleton instance
_cache_instance = None


def get_cache():
    """Get the singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LyricsCache()
    return _cache_instance
