import { motion, AnimatePresence } from 'framer-motion';
import useStore from '../hooks/useStore';

export default function NowPlaying() {
    const { currentSong } = useStore();

    return (
        <div className="glass p-5 mx-4 mt-4" style={{ borderRadius: 'var(--radius-lg, 24px)' }}>
            <AnimatePresence mode="wait">
                {currentSong ? (
                    <motion.div
                        key={`${currentSong.title}-${currentSong.artist}`}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.4 }}
                        className="flex items-center gap-4"
                    >
                        {/* Album Art Placeholder */}
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent-500 via-glow-purple to-glow-pink
              flex items-center justify-center shrink-0 shadow-lg"
                            style={{ boxShadow: '0 4px 20px rgba(99, 102, 241, 0.3)' }}>
                            <span className="text-2xl text-white">♫</span>
                        </div>

                        {/* Song Info */}
                        <div className="flex-1 min-w-0">
                            <h2 className="font-display font-bold text-lg truncate text-[var(--text-primary)]">
                                {currentSong.title}
                            </h2>
                            <p className="text-sm text-[var(--text-secondary)] truncate">
                                {currentSong.artist}
                                {currentSong.album && (
                                    <span className="text-[var(--text-muted)]"> · {currentSong.album}</span>
                                )}
                            </p>
                        </div>

                        {/* Source badge */}
                        <div className="shrink-0">
                            <span className="px-3 py-1 rounded-full text-xs font-medium
                bg-accent-500/10 text-accent-500 border border-accent-500/20">
                                {currentSong.source === 'smtc' ? 'System' :
                                    currentSong.source === 'acoustid' ? 'Fingerprint' :
                                        currentSong.source === 'manual' ? 'Search' : 'Detected'}
                            </span>
                        </div>
                    </motion.div>
                ) : (
                    <motion.div
                        key="waiting"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex items-center gap-4"
                    >
                        <div className="w-14 h-14 rounded-2xl bg-[var(--border-color)] flex items-center justify-center shrink-0">
                            <span className="text-2xl text-[var(--text-muted)]">♪</span>
                        </div>
                        <div>
                            <h2 className="font-display font-semibold text-lg text-[var(--text-muted)]">
                                Waiting for music...
                            </h2>
                            <p className="text-sm text-[var(--text-muted)]">
                                Play a song in any app to get started
                            </p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
