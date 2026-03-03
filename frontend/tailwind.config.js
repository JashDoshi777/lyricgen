/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
                display: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
            },
            colors: {
                surface: {
                    50: '#fafafa',
                    100: '#f4f4f5',
                    200: '#e4e4e7',
                    300: '#d4d4d8',
                    400: '#a1a1aa',
                    500: '#71717a',
                    600: '#52525b',
                    700: '#3f3f46',
                    800: '#27272a',
                    900: '#18181b',
                    950: '#09090b',
                },
                accent: {
                    DEFAULT: '#6366f1',
                    50: '#eef2ff',
                    100: '#e0e7ff',
                    200: '#c7d2fe',
                    300: '#a5b4fc',
                    400: '#818cf8',
                    500: '#6366f1',
                    600: '#4f46e5',
                    700: '#4338ca',
                },
                glow: {
                    purple: '#a855f7',
                    blue: '#3b82f6',
                    pink: '#ec4899',
                    cyan: '#06b6d4',
                }
            },
            backdropBlur: {
                xs: '2px',
                '2xl': '40px',
                '3xl': '64px',
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-out',
                'slide-up': 'slideUp 0.4s ease-out',
                'slide-down': 'slideDown 0.4s ease-out',
                'glow-pulse': 'glowPulse 2s ease-in-out infinite',
                'gradient-shift': 'gradientShift 8s ease infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideDown: {
                    '0%': { opacity: '0', transform: 'translateY(-20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                glowPulse: {
                    '0%, 100%': { opacity: '0.4' },
                    '50%': { opacity: '0.8' },
                },
                gradientShift: {
                    '0%, 100%': { backgroundPosition: '0% 50%' },
                    '50%': { backgroundPosition: '100% 50%' },
                },
            },
        },
    },
    plugins: [],
}
