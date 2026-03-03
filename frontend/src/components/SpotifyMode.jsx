import { useRef, useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';

export default function SpotifyMode({ lyrics, currentIndex, lineDuration, translations, onLineClick }) {
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
        <div className="flex flex-col items-center gap-1 py-20">
            {lyrics.map((line, i) => {
                const isActive = i === currentIndex;
                const isPast = i < currentIndex;
                const distance = Math.abs(i - currentIndex);
                const isNear = distance <= 2;

                // Determine opacity based on distance from active line
                let opacity = 0.25;
                if (isActive) opacity = 1;
                else if (distance === 1) opacity = 0.6;
                else if (distance === 2) opacity = 0.45;
                else if (distance === 3) opacity = 0.3;

                return (
                    <motion.div
                        key={i}
                        ref={isActive ? activeRef : null}
                        animate={{
                            opacity,
                            scale: isActive ? 1 : 1,
                            y: 0,
                        }}
                        transition={{
                            duration: 0.5,
                            ease: [0.25, 0.1, 0.25, 1],
                        }}
                        className={`
                            relative cursor-pointer text-center w-full max-w-3xl
                            rounded-2xl transition-colors duration-300
                            ${isActive
                                ? 'spotify-line-active py-4 px-8'
                                : 'py-2.5 px-6 hover:bg-white/5'
                            }
                        `}
                        onClick={() => onLineClick(line, i)}
                    >
                        {/* Active line progress bar — grows to match exact line duration */}
                        {isActive && (
                            <ProgressBar
                                key={`bar-${currentIndex}`}
                                durationMs={lineDuration}
                            />
                        )}

                        <p
                            className={`
                                font-display leading-relaxed transition-all duration-500
                                ${isActive
                                    ? 'text-xl md:text-2xl font-bold tracking-tight'
                                    : isPast
                                        ? 'text-lg md:text-xl font-normal text-[var(--text-muted)]'
                                        : isNear
                                            ? 'text-lg md:text-xl font-medium text-[var(--text-secondary)]'
                                            : 'text-base md:text-lg font-normal text-[var(--text-muted)]'
                                }
                            `}
                            style={isActive ? {
                                background: 'linear-gradient(135deg, #fff 0%, #e0e7ff 50%, #c7d2fe 100%)',
                                WebkitBackgroundClip: 'text',
                                WebkitTextFillColor: 'transparent',
                                backgroundClip: 'text',
                                textShadow: 'none',
                                filter: 'drop-shadow(0 0 30px rgba(99, 102, 241, 0.4))',
                            } : {}}
                        >
                            {line.text}
                        </p>

                        {/* Translation line */}
                        {translations[i] && translations[i] !== line.text && (
                            <p className={`
                                mt-1 italic transition-all duration-300
                                ${isActive
                                    ? 'text-sm text-[var(--accent)] opacity-80'
                                    : 'text-xs text-[var(--text-muted)] opacity-50'
                                }
                            `}>
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
 * Progress bar that animates from 0% → 100% over the exact line duration.
 * Uses CSS animation for silky smooth 60fps rendering.
 */
function ProgressBar({ durationMs }) {
    // Use a unique key per render to restart the animation
    const animationStyle = useMemo(() => ({
        position: 'absolute',
        left: 0,
        top: '50%',
        transform: 'translateY(-50%)',
        width: '3px',
        borderRadius: '9999px',
        background: 'linear-gradient(180deg, var(--accent), #a855f7)',
        boxShadow: '0 0 20px var(--accent-glow), 0 0 40px var(--accent-glow)',
        animation: `progressGrow ${durationMs}ms linear forwards`,
        height: '0%',
    }), [durationMs]);

    return (
        <>
            <style>{`
                @keyframes progressGrow {
                    from { height: 15%; }
                    to { height: 90%; }
                }
            `}</style>
            <div style={animationStyle} />
        </>
    );
}
