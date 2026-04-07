export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        accent: {
          50: '#effcf6',
          100: '#d7f9e8',
          200: '#b1f0d1',
          300: '#7ee2b3',
          400: '#47cd8f',
          500: '#22b573',
          600: '#158a57',
          700: '#136d47',
          800: '#12563b',
          900: '#114732',
        },
        ink: {
          950: '#07130f',
          900: '#0d1f1a',
          800: '#14332a',
          700: '#1d4a3c',
        },
      },
      fontFamily: {
        sans: ['Manrope', 'Inter', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'Manrope', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
