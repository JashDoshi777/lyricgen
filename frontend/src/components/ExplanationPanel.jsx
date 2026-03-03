import { motion, AnimatePresence } from 'framer-motion';
import useStore from '../hooks/useStore';

export default function ExplanationPanel() {
    const { explanation, explanationLoading, showExplanation, closeExplanation } = useStore();

    return (
        <AnimatePresence>
            {showExplanation && (
                <motion.div
                    initial={{ opacity: 0, x: 30, width: 0 }}
                    animate={{ opacity: 1, x: 0, width: 340 }}
                    exit={{ opacity: 0, x: 30, width: 0 }}
                    transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
                    className="glass overflow-hidden shrink-0"
                    style={{ borderRadius: 'var(--radius-lg, 24px)', maxHeight: 'calc(100vh - 240px)' }}
                >
                    <div className="p-5 h-full overflow-y-auto">
                        {/* Header */}
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent-500 to-glow-pink
                  flex items-center justify-center">
                                    <span className="text-white text-xs">AI</span>
                                </div>
                                <h3 className="font-display font-bold text-sm text-[var(--text-primary)]">
                                    Lyric Insight
                                </h3>
                            </div>
                            <button
                                onClick={closeExplanation}
                                className="w-7 h-7 rounded-lg bg-[var(--border-color)] flex items-center justify-center
                  text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors text-xs"
                            >
                                ✕
                            </button>
                        </div>

                        {explanationLoading ? (
                            <div className="space-y-3">
                                <div className="h-4 rounded-full bg-[var(--border-color)] animate-pulse w-3/4" />
                                <div className="h-4 rounded-full bg-[var(--border-color)] animate-pulse w-full" />
                                <div className="h-4 rounded-full bg-[var(--border-color)] animate-pulse w-2/3" />
                                <div className="h-3 rounded-full bg-[var(--border-color)] animate-pulse w-1/2 mt-6" />
                                <div className="h-4 rounded-full bg-[var(--border-color)] animate-pulse w-full" />
                                <div className="h-4 rounded-full bg-[var(--border-color)] animate-pulse w-5/6" />
                            </div>
                        ) : explanation ? (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="space-y-4"
                            >
                                {/* Lyric line */}
                                <div className="p-3 rounded-xl bg-accent-500/10 border border-accent-500/20">
                                    <p className="text-sm font-medium text-accent-500 italic">
                                        "{explanation.line}"
                                    </p>
                                </div>

                                {/* Emotion tag */}
                                <div>
                                    <span className="px-3 py-1 rounded-full text-xs font-semibold
                    bg-glow-purple/10 text-glow-purple border border-glow-purple/20">
                                        {explanation.emotion}
                                    </span>
                                </div>

                                {/* Meaning */}
                                <div>
                                    <h4 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
                                        Meaning
                                    </h4>
                                    <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                                        {explanation.meaning}
                                    </p>
                                </div>

                                {/* Explanation */}
                                <div>
                                    <h4 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
                                        In Simple Terms
                                    </h4>
                                    <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                                        {explanation.explanation}
                                    </p>
                                </div>
                            </motion.div>
                        ) : null}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
