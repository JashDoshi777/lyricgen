import { useRef, useEffect, memo } from 'react';

/**
 * SpotifyMode — Lightweight, pure CSS version.
 * 
 * NO framer-motion. NO JavaScript animations.
 * All transitions handled via CSS opacity/transform transitions.
 * Only the active line triggers a re-render via currentIndex change.
 */

const SpotifyMode = memo(function SpotifyMode({ lyrics, currentIndex, lineDuration, translations, onLineClick }) {
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
        <div className="flex flex-col items-center gap-1 py-20">
            {lyrics.map((line, i) => {
                const isActive = i === currentIndex;
                const isPast = i < currentIndex;
                const distance = Math.abs(i - currentIndex);

                // CSS-only opacity via inline style
                let opacity = 0.25;
                if (isActive) opacity = 1;
                else if (distance === 1) opacity = 0.6;
                else if (distance === 2) opacity = 0.45;
                else if (distance === 3) opacity = 0.3;

                return (
                    <div
                        key={i}
                        ref={isActive ? activeRef : null}
                        className={`
                            relative cursor-pointer text-center w-full max-w-3xl
                            rounded-2xl
                            ${isActive ? 'spotify-line-active py-4 px-8' : 'py-2.5 px-6 hover:bg-white/5'}
                        `}
                        style={{
                            opacity,
                            transition: 'opacity 0.4s ease, transform 0.3s ease',
                        }}
                        onClick={() => onLineClick(line, i)}
                    >
                        {/* Active progress bar — pure CSS animation */}
                        {isActive && (
                            <div
                                key={`bar-${currentIndex}`}
                                className="spotify-progress-bar"
                                style={{ animationDuration: `${lineDuration}ms` }}
                            />
                        )}

                        <p
                            className={`
                                font-display leading-relaxed
                                ${isActive
                                    ? 'text-xl md:text-2xl font-bold tracking-tight spotify-active-text'
                                    : isPast
                                        ? 'text-lg md:text-xl font-normal text-[var(--text-muted)]'
                                        : distance <= 2
                                            ? 'text-lg md:text-xl font-medium text-[var(--text-secondary)]'
                                            : 'text-base md:text-lg font-normal text-[var(--text-muted)]'
                                }
                            `}
                        >
                            {line.text}
                        </p>

                        {translations[i] && translations[i] !== line.text && (
                            <p className={`
                                mt-1 italic
                                ${isActive
                                    ? 'text-sm text-[var(--accent)] opacity-80'
                                    : 'text-xs text-[var(--text-muted)] opacity-50'
                                }
                            `}>
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

export default SpotifyMode;
