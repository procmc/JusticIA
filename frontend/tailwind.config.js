/** @type {import('tailwindcss').Config} */
const { heroui } = require("@heroui/react");

module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}",
  ],
  important: true,
  theme: {
    extend: {
      colors: {
        azulOscuro: "#0D3858",
        primario: "#0b72eb",
        cabecera: "#398cebff",
        fondoLogin: "#fcfbfb",
        celeste: "#38b6ff",
        tituloSeccion: "#1e3a8a", // Color estándar para títulos de secciones
      },
    },
  },
  darkMode: 'media',
  plugins: [heroui()],  
};