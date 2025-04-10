// 記事生成の入力フォームの型定義
export interface ArticleGenerationFormData {
  mainKeywords: string; // メインキーワード
  articleTheme: string; // 記事のテーマ・概要
  targetAudience?: string; // ターゲット読者層
  tone?: 'formal' | 'casual' | 'professional' | 'friendly'; // 文体
  excludeKeywords?: string; // 除外キーワード
  referenceUrls?: string; // 参考URL
  companyInfo?: string; // クライアントの会社情報・サービス情報
}

// 記事構成案の型定義
export interface ArticleOutline {
  id: string;
  title: string;
  sections: ArticleSection[];
}

// 記事セクションの型定義
export interface ArticleSection {
  id: string;
  level: 'h2' | 'h3' | 'h4';
  title: string;
  keywords?: string[]; // このセクションに含めるべきキーワード
  content?: string; // 生成後のコンテンツ
}

// 生成された記事の型定義
export interface GeneratedArticle {
  id: string;
  title: string;
  metaDescription: string;
  sections: ArticleSection[];
  createdAt: string;
  updatedAt: string;
  status: 'draft' | 'published';
}

// SEO分析結果の型定義
export interface SeoAnalysisResult {
  mainKeyword: string;
  searchVolume?: number;
  difficulty?: number;
  relatedKeywords: string[];
  suggestedKeywords: string[];
  lsiKeywords: string[];
  questionsKeywords: string[];
}

// APIレスポンスの型定義
export interface ApiResponse<T> {
  data?: T;
  error?: string;
}
