/** @type {import('tailwindcss').Config} */
module.exports = {
  // --- 关键修正：启用 class 模式的暗黑主题 ---
  darkMode: 'class',
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      // 这是暗黑模式下的颜色
      colors: {
        'primary-bg': '#10101A',
        'secondary-bg': '#181828',
        'sidebar-bg': '#141420',
        'primary-accent': '#7F5AF0',
        'secondary-accent': '#2CB67D',
        'primary-text': '#FFFFFE',
        'secondary-text': '#94A1B2',
        'danger': '#EF4444',
        'warning': '#F59E0B',
      }
    },
  },
  plugins: [],
}
