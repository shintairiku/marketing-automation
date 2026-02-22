/** @type {import('next').NextConfig} */
const nextConfig = {
  // dev (.next) と build (.next-build) で出力先を分離し、
  // bun run dev 中に bun run build しても dev が壊れないようにする。
  distDir: process.env.NEXT_BUILD_DIR || '.next',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'storage.googleapis.com',
        port: '',
        pathname: `/${process.env.NEXT_PUBLIC_GCS_BUCKET_NAME || 'marketing-automation-images'}/**`,
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
  async headers() {
    return [
      {
        // Service Worker: no-cache + correct Content-Type
        source: '/sw.js',
        headers: [
          {
            key: 'Content-Type',
            value: 'application/javascript; charset=utf-8',
          },
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
