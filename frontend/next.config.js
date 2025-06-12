/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // Docker環境でのビルドを考慮
  async rewrites() {
    return [
      {
        source: '/api/proxy/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;