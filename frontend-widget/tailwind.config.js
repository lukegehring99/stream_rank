/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Vibrant Canva-inspired palette
        primary: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#00C4CC',  // Canva teal
          600: '#00a8b0',
          700: '#008b91',
          800: '#006e73',
          900: '#005156',
          950: '#003538',
        },
        // Hot pink/magenta accent
        accent: {
          50: '#fdf2f8',
          100: '#fce7f3',
          200: '#fbcfe8',
          300: '#f9a8d4',
          400: '#f472b6',
          500: '#7B2FF7',  // Vibrant purple
          600: '#6922d4',
          700: '#5715b1',
          800: '#45098e',
          900: '#33006b',
          950: '#210048',
        },
        // Coral/orange for energy
        coral: {
          400: '#FF7F6E',
          500: '#FF6B57',
          600: '#E55A47',
        },
        // Sunny yellow
        sunny: {
          400: '#FFD93D',
          500: '#FFC800',
          600: '#E5B400',
        },
        // Clean surface colors
        surface: {
          light: '#ffffff',
          'light-alt': '#fafafa',
          dark: '#0a0a0a',
          'dark-alt': '#171717',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'soft': '0 2px 8px rgba(0, 0, 0, 0.04), 0 4px 24px rgba(0, 0, 0, 0.06)',
        'soft-lg': '0 4px 16px rgba(0, 0, 0, 0.08), 0 8px 32px rgba(0, 0, 0, 0.08)',
        'glow': '0 0 20px rgba(0, 196, 204, 0.3)',
        'glow-purple': '0 0 20px rgba(123, 47, 247, 0.3)',
        'glow-coral': '0 0 20px rgba(255, 107, 87, 0.3)',
        'pop': '0 4px 20px rgba(123, 47, 247, 0.15), 0 8px 40px rgba(0, 196, 204, 0.1)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-candy': 'linear-gradient(135deg, #00C4CC 0%, #7B2FF7 50%, #FF6B57 100%)',
        'gradient-sunset': 'linear-gradient(135deg, #FF6B57 0%, #7B2FF7 100%)',
        'gradient-ocean': 'linear-gradient(135deg, #00C4CC 0%, #7B2FF7 100%)',
        'gradient-warm': 'linear-gradient(135deg, #FFD93D 0%, #FF6B57 100%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-soft': 'pulseSoft 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
};
