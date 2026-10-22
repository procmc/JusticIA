/** @type {import('next').NextConfig} */
const nextConfig = {
  // La red de seguridad de extremo a extremo compila en su propia carpeta (.next-e2e) para no tocar la de desarrollo.
  distDir: process.env.NEXT_DIST_DIR || '.next',
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
