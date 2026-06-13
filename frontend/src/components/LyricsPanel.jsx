import { useRef, useEffect, useCallback } from 'react';
import useStore from '../hooks/useStore';
import SpotifyMode from './SpotifyMode';
import KaraokeMode from './KaraokeMode';
import ExplanationPanel from './ExplanationPanel';

const BACKEND_URL = 'http://localhost:5000';

export default function LyricsPanel() {
    const {
        lyrics,
        currentLineIndex,
        currentLineDuration,
        displayMode,
        currentSong,
        translationEnabled,
        targetLanguage,
        translations,
        setTranslations,
        setExplanation,
        setExplanationLoading,
    } = useStore();

    const containerRef = useRef(null);

    // Fetch translations when enabled
    useEffect(() => {
        if (translationEnabled && lyrics.length > 0) {
            fetch(`${BACKEND_URL}/api/translate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lines: lyrics,
                    target_lang: targetLanguage,
                }),
            })
                .then((r) => r.json())
                .then((data) => {
                    const transMap = {};
                    (data.lines || []).forEach((line, i) => {
                        transMap[i] = line.translation;
                    });
                    setTranslations(transMap);
                })
                .catch(() => { });
        }
    }, [translationEnabled, targetLanguage, lyrics]);

    // Handle lyric click for AI explanation
    const handleLyricClick = useCallback(
        (line, index) => {
            setExplanationLoading(true);

            const contextLines = [];
            for (let i = Math.max(0, index - 2); i <= Math.min(lyrics.length - 1, index + 2); i++) {
                if (i !== index) contextLines.push(lyrics[i].text);
            }

            fetch(`${BACKEND_URL}/api/explain`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    line: line.text,
                    title: currentSong?.title || '',
                    artist: currentSong?.artist || '',
                    context: contextLines,
                }),
            })
                .then((r) => r.json())
                .then((data) => setExplanation({ ...data, line: line.text }))
                .catch(() =>
                    setExplanation({
                        line: line.text,
                        meaning: 'Could not load explanation.',
                        emotion: 'Unknown',
                        explanation: 'Check your backend connection.',
                    })
                );
        },
        [lyrics, currentSong]
    );

    if (lyrics.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center">
                    <div className="text-6xl mb-4 opacity-20">♫</div>
                    <p className="text-[var(--text-muted)] text-lg font-medium">
                        No lyrics loaded
                    </p>
                    <p className="text-[var(--text-muted)] text-sm mt-1 opacity-60">
                        Lyrics will appear when a song is detected
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-1 gap-4 mx-4 mt-4 overflow-hidden">
            {/* Main lyrics area */}
            <div
                ref={containerRef}
                className="flex-1 glass overflow-y-auto p-6 relative"
                style={{ borderRadius: 'var(--radius-lg, 24px)', maxHeight: 'calc(100vh - 240px)' }}
            >
                {displayMode === 'karaoke' ? (
                    <KaraokeMode
                        lyrics={lyrics}
                        currentIndex={currentLineIndex}
                        lineDuration={currentLineDuration}
                        translations={translationEnabled ? translations : {}}
                        onLineClick={handleLyricClick}
                    />
                ) : (
                    <SpotifyMode
                        lyrics={lyrics}
                        currentIndex={currentLineIndex}
                        lineDuration={currentLineDuration}
                        translations={translationEnabled ? translations : {}}
                        onLineClick={handleLyricClick}
                    />
                )}
            </div>

            {/* Explanation panel (conditional) */}
            <ExplanationPanel />
        </div>
    );
}
