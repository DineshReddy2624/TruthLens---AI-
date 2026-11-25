/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'verdict-supported': '#16a34a',
        'verdict-contradicted': '#dc2626',
        'verdict-partial': '#f59e0b',
        'verdict-insufficient': '#6b7280',
        'verdict-conflicting': '#7c3aed',
      },
    },
  },
  plugins: [],
};
