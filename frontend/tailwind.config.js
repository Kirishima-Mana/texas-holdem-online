/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        poker: {
          green: '#0a7e3a',
          dark: '#1a1a1a',
          gold: '#ffd700',
          red: '#dc2626',
          blue: '#2563eb',
        }
      },
      animation: {
        'chip-bounce': 'bounce 1s infinite',
        'card-deal': 'deal 0.5s ease-out',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        deal: {
          '0%': { transform: 'translateY(-100px) rotateY(180deg)', opacity: '0' },
          '100%': { transform: 'translateY(0) rotateY(0)', opacity: '1' },
        }
      }
    },
  },
  plugins: [],
}