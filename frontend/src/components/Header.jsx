import { motion } from 'framer-motion';
import useStore from '../hooks/useStore';

export default function Header() {
    const { theme, toggleTheme, connected, activePanel, setActivePanel } = useStore();

    const navItems = [
        { id: 'lyrics', label: 'Lyrics', icon: '♫' },
        { id: 'history', label: 'History', icon: '⏱' },
        { id: 'settings', label: 'Settings', icon: '⚙' },
    ];

    return (
        <header className="glass sticky top-0 z-50 px-6 py-3 mx-4 mt-4 flex items-center justify-between"
            style={{ borderRadius: 'var(--radius)' }}>
            {/* Logo */}
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-500 to-glow-purple flex items-center justify-center">
                    <span className="text-white text-sm font-bold">♪</span>
                </div>
                <h1 className="font-display font-bold text-lg tracking-tight">
                    <span className="text-gradient">LiveLyrics</span>
                </h1>
            </div>

            {/* Navigation */}
            <nav className="flex items-center gap-1">
                {navItems.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => setActivePanel(item.id)}
                        className={`relative px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300
              ${activePanel === item.id
                                ? 'text-accent-500'
                                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                            }`}
                    >
                        {activePanel === item.id && (
                            <motion.div
                                layoutId="nav-pill"
                                className="absolute inset-0 rounded-xl"
                                style={{ background: 'var(--accent-glow)' }}
                                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                            />
                        )}
                        <span className="relative z-10 flex items-center gap-1.5">
                            <span>{item.icon}</span>
                            <span className="hidden sm:inline">{item.label}</span>
                        </span>
                    </button>
                ))}
            </nav>

            {/* Right side */}
            <div className="flex items-center gap-3">
                {/* Connection status */}
                <div className="flex items-center gap-2 text-xs">
                    <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400' : 'bg-red-400'} animate-pulse`} />
                    <span className="text-[var(--text-muted)] hidden sm:inline">
                        {connected ? 'Connected' : 'Disconnected'}
                    </span>
                </div>

                {/* Theme toggle */}
                <button
                    onClick={toggleTheme}
                    className="theme-toggle"
                    aria-label="Toggle theme"
                    title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                />
            </div>
        </header>
    );
}
