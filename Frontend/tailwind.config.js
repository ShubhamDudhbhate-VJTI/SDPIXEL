/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1976d2',
        success: '#2e7d32',
        warning: '#ef6c00',
        danger: '#c62828',
        background: '#fafafa',
        surface: '#ffffff',
        text: {
          primary: '#212121',
          secondary: '#757575'
        }
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': {
            boxShadow: '0 0 20px rgba(198, 40, 40, 0.4)',
          },
          '50%': {
            boxShadow: '0 0 30px rgba(198, 40, 40, 0.6)',
          },
        },
      },
    },
  },
  plugins: [],
}
