export const mockCompanyData = {
  id: 'mock-company-1',
  name: 'Shintairiku Labs',
  website_url: 'https://marketing.local',
  description: 'AIを活用したSEO記事制作支援を行う検証用の架空企業です。',
  usp: 'マーケティング×AIの実績を活かした高速なSEOコンテンツ制作',
  target_persona: 'B2B SaaSのマーケティング担当者',
  is_default: true,
  brand_slogan: 'マーケをもっとクリエイティブに',
  target_keywords: 'SEO, コンテンツマーケ, リード獲得',
  industry_terms: 'SERP, CTA, KPI',
  avoid_terms: '無料, 格安',
  popular_articles: 'https://marketing.local/blog/ai-seo-beginner',
  target_area: '日本国内',
  created_at: '2024-01-01T00:00:00.000Z',
  updated_at: '2024-01-01T00:00:00.000Z',
};

export const isCompanyMockEnabled =
  process.env.NEXT_PUBLIC_ENABLE_COMPANY_MOCK === 'true' &&
  process.env.NODE_ENV !== 'production';
