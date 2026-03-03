import { useRef, useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';

export default function KaraokeMode({ lyrics, currentIndex, lineDuration, translations, onLineClick }) {
    const activeRef = useRef(null);

    // Auto-scroll: find the scrollable parent and scroll the active line to center
    useEffect(() => {
        if (!activeRef.current) return;

        const scrollParent = activeRef.current.closest('.overflow-y-auto');
        if (!scrollParent) return;

        const container = scrollParent;
        const el = activeRef.current;
        const containerRect = container.getBoundingClientRect();
        const elRect = el.getBoundingClientRect();

        const elCenterOffset = elRect.top - containerRect.top + container.scrollTop;
        const targetScroll = elCenterOffset - containerRect.height / 2 + elRect.height / 2;

        container.scrollTo({
            top: targetScroll,
            behavior: 'smooth',
        });
    }, [currentIndex]);

    return (
        <div className="flex flex-col items-center gap-3 py-16">
            {lyrics.map((line, i) => {
                const isActive = i === currentIndex;
                const isPast = i < currentIndex;
                const distance = Math.abs(i - currentIndex);

                return (
                    <motion.div
                        key={i}
                        ref={isActive ? activeRef : null}
                        animate={{
                            opacity: isActive ? 1 : distance <= 2 ? 0.6 : 0.25,
                            scale: isActive ? 1.05 : 1,
                        }}
                        transition={{ duration: 0.3 }}
                        className="cursor-pointer text-center px-6 py-2 rounded-xl w-full max-w-2xl
              hover:bg-[var(--border-color)] transition-colors"
                        onClick={() => onLineClick(line, i)}
                    >
                        <p className="font-display text-xl md:text-2xl font-semibold leading-relaxed">
                            {isActive ? (
                                <KaraokeWords
                                    key={`karaoke-${currentIndex}`}
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
                    </motion.div>
                );
            })}

            {/* Bottom spacer so last lyrics can scroll to center */}
            <div className="h-[40vh]" />
        </div>
    );
}

/**
 * Word-level karaoke animation using requestAnimationFrame.
 * 
 * Distributes the real line duration across words weighted by character count,
 * so longer words get proportionally more time. Uses rAF for smooth, accurate timing.
 */
function KaraokeWords({ text, durationMs }) {
    const words = useMemo(() => text.split(/\s+/).filter(Boolean), [text]);
    const [progress, setProgress] = useState(0); // 0..1

    // Compute word boundaries (0..1) weighted by character length
    const wordBoundaries = useMemo(() => {
        if (!words.length) return [];
        const totalChars = words.reduce((sum, w) => sum + w.length, 0);
        const boundaries = [];
        let cumulative = 0;
        for (const word of words) {
            boundaries.push(cumulative / totalChars);
            cumulative += word.length;
        }
        return boundaries;
    }, [words]);

    // rAF-driven progress animation — exactly matches line duration
    useEffect(() => {
        if (!words.length || durationMs <= 0) return;

        const startTime = performance.now();
        let rafId;

        const animate = (now) => {
            const elapsed = now - startTime;
            const p = Math.min(elapsed / durationMs, 1);
            setProgress(p);

            if (p < 1) {
                rafId = requestAnimationFrame(animate);
            }
        };

        rafId = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(rafId);
    }, [text, durationMs, words.length]);

    return (
        <span>
            {words.map((word, i) => {
                // A word is "active" when progress passes its boundary
                const wordStart = wordBoundaries[i] || 0;
                const wordEnd = i + 1 < wordBoundaries.length ? wordBoundaries[i + 1] : 1;
                const isWordActive = progress >= wordStart;

                // Per-word fill progress (0..1) for smooth gradient effect
                let wordProgress = 0;
                if (progress >= wordEnd) {
                    wordProgress = 1;
                } else if (progress > wordStart) {
                    wordProgress = (progress - wordStart) / (wordEnd - wordStart);
                }

                return (
                    <span
                        key={i}
                        className="inline-block mr-1.5 font-bold transition-none"
                        style={{
                            background: isWordActive
                                ? `linear-gradient(90deg, var(--accent) ${wordProgress * 100}%, var(--text-secondary) ${wordProgress * 100}%)`
                                : 'none',
                            color: isWordActive ? 'transparent' : 'var(--text-secondary)',
                            WebkitBackgroundClip: isWordActive ? 'text' : 'unset',
                            backgroundClip: isWordActive ? 'text' : 'unset',
                            WebkitTextFillColor: isWordActive ? 'transparent' : 'var(--text-secondary)',
                            textShadow: isWordActive && wordProgress > 0.5
                                ? '0 0 20px var(--accent-glow)'
                                : 'none',
                        }}
                    >
                        {word}
                    </span>
                );
            })}
        </span>
    );
}
