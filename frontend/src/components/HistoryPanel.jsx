import { motion } from 'framer-motion';
import useStore from '../hooks/useStore';

export default function HistoryPanel() {
    const { history } = useStore();

    return (
        <div className="flex-1 mx-4 mt-4">
            <div className="glass p-6" style={{ borderRadius: 'var(--radius-lg, 24px)', maxHeight: 'calc(100vh - 240px)', overflow: 'auto' }}>
                <h2 className="font-display font-bold text-xl mb-4 text-[var(--text-primary)]">
                    Recently Played
                </h2>

                {history.length === 0 ? (
                    <div className="text-center py-12">
                        <div className="text-4xl mb-3 opacity-20">⏱</div>
                        <p className="text-[var(--text-muted)]">No songs in history yet</p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {history.map((song, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.05 }}
                                className="flex items-center gap-3 p-3 rounded-xl hover:bg-[var(--border-color)]
                  transition-colors cursor-pointer group"
                            >
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-500/20 to-glow-purple/20
                  flex items-center justify-center shrink-0">
                                    <span className="text-accent-500 text-sm">♫</span>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium text-sm truncate text-[var(--text-primary)]">
                                        {song.title}
                                    </p>
                                    <p className="text-xs text-[var(--text-muted)] truncate">
                                        {song.artist}
                                    </p>
                                </div>
                                <span className="text-xs text-[var(--text-muted)] shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                    {formatTime(song.played_at)}
                                </span>
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return date.toLocaleDateString();
}
