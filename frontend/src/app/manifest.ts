import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'BlogAI - AIブログ記事自動生成',
    short_name: 'BlogAI',
    description:
      'AIを活用したブログ記事自動生成サービス。あなたのWordPressサイトに最適な記事を生成します。',
    start_url: '/',
    display: 'standalone',
    background_color: '#0f172a',
    theme_color: '#0f172a',
    orientation: 'portrait-primary',
    categories: ['productivity', 'business'],
    lang: 'ja',
    dir: 'ltr',
    icons: [
      {
        src: '/icon-192.png',
        sizes: '192x192',
        type: 'image/png',
      },
      {
        src: '/icon-256.png',
        sizes: '256x256',
        type: 'image/png',
      },
      {
        src: '/icon-384.png',
        sizes: '384x384',
        type: 'image/png',
      },
      {
        src: '/icon-512.png',
        sizes: '512x512',
        type: 'image/png',
      },
      {
        src: '/icon-maskable-192.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'maskable',
      },
      {
        src: '/icon-maskable-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
  };
}
