/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== 'production';

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.VERCEL ? '/api/:path*' : 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
