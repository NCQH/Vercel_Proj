/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      // Keep NextAuth endpoints handled by Next.js
      {
        source: '/api/auth/:path*',
        destination: '/api/auth/:path*',
      },
      // Proxy backend API routes in local development
      {
        source: '/api/:path*',
        destination: process.env.VERCEL ? '/api/:path*' : 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
