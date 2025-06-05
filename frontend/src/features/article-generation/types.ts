export interface GeneratedArticle {
  id: string;
  title: string;
  content: string;
  status: 'draft' | 'published' | 'archived';
  category?: string;
  tags?: string[];
  slug: string;
  createdAt: string;
  updatedAt: string;
} 