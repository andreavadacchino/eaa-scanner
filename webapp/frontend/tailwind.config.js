/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#2563eb',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
      },
      boxShadow: {
        'eaa-sm': '0 2px 4px rgba(0,0,0,0.06)',
        'eaa-md': '0 4px 10px rgba(0,0,0,0.08)',
        'eaa-lg': '0 10px 20px rgba(0,0,0,0.10)'
      },
      borderRadius: {
        'eaa': '12px'
      }
    },
  },
  plugins: [],
}
