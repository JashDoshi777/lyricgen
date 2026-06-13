import { useRef, useEffect, memo } from 'react';

/**
 * KaraokeMode — Lightweight, pure CSS version.
 * 
 * NO framer-motion. NO requestAnimationFrame. NO useState for animation.
 * Word highlighting uses a single CSS animation per active line.
 * Zero React re-renders during animation.
 */

const KaraokeMode = memo(function KaraokeMode({ lyrics, currentIndex, lineDuration, translations, onLineClick }) {
    const activeRef = useRef(null);

    // Auto-scroll active line to center
    useEffect(() => {
        if (!activeRef.current) return;
        const scrollParent = activeRef.current.closest('.overflow-y-auto');
        if (!scrollParent) return;

        const containerRect = scrollParent.getBoundingClientRect();
        const elRect = activeRef.current.getBoundingClientRect();
        const targetScroll = elRect.top - containerRect.top + scrollParent.scrollTop
            - containerRect.height / 2 + elRect.height / 2;

        scrollParent.scrollTo({ top: targetScroll, behavior: 'smooth' });
    }, [currentIndex]);

    return (
        <div className="flex flex-col items-center gap-3 py-16">
            {lyrics.map((line, i) => {
                const isActive = i === currentIndex;
                const isPast = i < currentIndex;
                const distance = Math.abs(i - currentIndex);
                const opacity = isActive ? 1 : distance <= 2 ? 0.6 : 0.25;

                return (
                    <div
                        key={i}
                        ref={isActive ? activeRef : null}
                        className="cursor-pointer text-center px-6 py-2 rounded-xl w-full max-w-2xl
                            hover:bg-[var(--border-color)]"
                        style={{
                            opacity,
                            transform: isActive ? 'scale(1.05)' : 'scale(1)',
                            transition: 'opacity 0.3s ease, transform 0.3s ease',
                        }}
                        onClick={() => onLineClick(line, i)}
                    >
                        <p className="font-display text-xl md:text-2xl font-semibold leading-relaxed">
                            {isActive ? (
                                <KaraokeWords
                                    key={`k-${currentIndex}`}
                                    text={line.text}
                                    durationMs={lineDuration}
                                />
                            ) : (
                                <span className={isPast ? 'text-[var(--text-muted)]' : 'text-[var(--text-secondary)]'}>
                                    {line.text}
                                </span>
                            )}
                        </p>
                        {translations[i] && translations[i] !== line.text && (
                            <p className="text-sm mt-1 opacity-50 italic text-[var(--text-secondary)]">
                                {translations[i]}
                            </p>
                        )}
                    </div>
                );
            })}
            <div className="h-[40vh]" />
        </div>
    );
});

export default KaraokeMode;

/**
 * Word-level karaoke — PURE CSS, zero JS animation.
 * 
 * Uses a single CSS @keyframes that sweeps a gradient across the entire line.
 * Each word is positioned inline and the gradient covers them sequentially
 * based on their character-offset percentage. No rAF, no setState, no re-renders.
 */
function KaraokeWords({ text, durationMs }) {
    const words = text.split(/\s+/).filter(Boolean);
    if (!words.length) return <span>{text}</span>;

    return (
        <span
            className="karaoke-sweep"
            style={{
                animationDuration: `${durationMs}ms`,
            }}
        >
            {words.map((word, i) => (
                <span key={i} className="inline-block mr-1.5 font-bold">
                    {word}
                </span>
            ))}
        </span>
    );
}
