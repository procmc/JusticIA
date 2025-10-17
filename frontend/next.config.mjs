/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // Desactivado para evitar double-render y duplicación de registros en bitácora
  allowedDevOrigins: [
    'http://localhost:3000',
    'http://192.168.1.254:3000',
  ],
  images: {
    // Configuración moderna para dominios remotos
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'http',
        hostname: '127.0.0.1',
      },
      {
        protocol: 'http',
        hostname: '192.168.1.254',
      },
    ],
    // Formatos soportados
    formats: ['image/webp', 'image/avif'],
  },
};

export default nextConfig;
