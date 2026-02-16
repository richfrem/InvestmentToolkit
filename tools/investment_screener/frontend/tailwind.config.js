/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                background: '#020617', // slate-950
                surface: '#0f172a',    // slate-900
                primary: '#f59e0b',    // amber-500 (Gold)
                secondary: '#94a3b8',  // slate-400
                text: '#e2e8f0',       // slate-200
                accent: '#fbbf24',     // amber-400
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
