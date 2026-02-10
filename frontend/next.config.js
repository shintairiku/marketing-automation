/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'storage.googleapis.com',
        port: '',
        pathname: '/marketing-automation-images/**',
      },
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
    ],
  },
  experimental: {
    // Extend proxy timeout so long-running agent edits don't get reset by Next.js dev/prod proxy.
    proxyTimeout: 120_000,
  },
  // rewrites は削除: Cloud Run 非公開化に伴い、全リクエストを route handler 経由に集約。
  // route handler で X-Serverless-Authorization (Google ID Token) を付与する。
};

module.exports = nextConfig;
