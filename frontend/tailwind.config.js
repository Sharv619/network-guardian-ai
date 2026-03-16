/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Use distinctive fonts - avoid generic Inter/Arial
        sans: ['Outfit', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        // Custom color palette - avoid generic purple/blue gradients
        // Using a more sophisticated dark theme with warm undertones
        surface: {
          50: '#f8f7f4',
          100: '#f0ede8',
          200: '#e2ddd5',
          300: '#cec5b9',
          400: '#b8ab99',
          500: '#a3907e',
          600: '#8f7968',
          700: '#756053',
          800: '#5f4b43',
          900: '#4d3d37',
          950: '#2a211d',
        },
        accent: {
          DEFAULT: '#e07a5f', // Terracotta - warm, distinctive
          light: '#f4a393',
          dark: '#c45a3f',
          muted: '#d4a593',
        },
        // Status colors - more refined
        success: {
          DEFAULT: '#81b29a',
          light: '#a8d5ba',
          dark: '#5f9a7a',
        },
        warning: {
          DEFAULT: '#f2cc8f',
          light: '#f7dfb5',
          dark: '#d4a96a',
        },
        danger: {
          DEFAULT: '#e07a5f',
          light: '#f4a393',
          dark: '#c45a3f',
        },
        // Dark theme base - warm charcoal instead of cold slate
        dark: {
          50: '#f5f4f1',
          100: '#e8e5e0',
          200: '#d4cfc6',
          300: '#b8b0a1',
          400: '#9c917a',
          500: '#857766',
          600: '#6e6054',
          700: '#574c42',
          800: '#464035',
          900: '#3b342c',
          950: '#252018',
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'glow': '0 0 20px rgba(224, 122, 95, 0.15)',
      },
    },
  },
  plugins: [],
}
