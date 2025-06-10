'use client';

import { cn } from '@/lib/utils';

interface ArticlePreviewStylesProps {
  children: React.ReactNode;
  className?: string;
}

export default function ArticlePreviewStyles({ children, className }: ArticlePreviewStylesProps) {
  return (
    <div className={cn(
      "prose prose-lg max-w-none",
      // 基本的な文字設定
      "text-foreground leading-relaxed",
      
      // 見出しスタイル
      "prose-headings:text-foreground prose-headings:font-bold prose-headings:tracking-tight",
      "prose-h1:text-3xl prose-h1:mb-6 prose-h1:mt-8 prose-h1:border-b prose-h1:border-border prose-h1:pb-3",
      "prose-h2:text-2xl prose-h2:mb-4 prose-h2:mt-8 prose-h2:text-primary",
      "prose-h3:text-xl prose-h3:mb-3 prose-h3:mt-6 prose-h3:text-secondary",
      "prose-h4:text-lg prose-h4:mb-2 prose-h4:mt-4",
      
      // 段落とリストのスタイル
      "prose-p:mb-4 prose-p:text-base prose-p:leading-relaxed",
      "prose-ul:mb-4 prose-ul:space-y-2",
      "prose-ol:mb-4 prose-ol:space-y-2",
      "prose-li:text-base prose-li:leading-relaxed",
      
      // リンクスタイル
      "prose-a:text-primary prose-a:no-underline prose-a:font-medium",
      "prose-a:border-b prose-a:border-primary/30",
      "hover:prose-a:border-primary/60 hover:prose-a:text-primary/80",
      
      // 強調・太字
      "prose-strong:text-foreground prose-strong:font-semibold",
      "prose-em:text-muted-foreground prose-em:italic",
      
      // 引用
      "prose-blockquote:border-l-4 prose-blockquote:border-primary/30",
      "prose-blockquote:bg-muted/30 prose-blockquote:py-2 prose-blockquote:px-4",
      "prose-blockquote:my-6 prose-blockquote:italic prose-blockquote:text-muted-foreground",
      
      // コードブロック
      "prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5",
      "prose-code:rounded prose-code:text-sm prose-code:text-foreground",
      "prose-pre:bg-muted prose-pre:p-4 prose-pre:rounded-lg",
      "prose-pre:overflow-x-auto prose-pre:text-sm",
      
      // テーブル
      "prose-table:w-full prose-table:border-collapse",
      "prose-thead:border-b prose-thead:border-border",
      "prose-th:text-left prose-th:font-semibold prose-th:py-2 prose-th:px-3",
      "prose-td:py-2 prose-td:px-3 prose-td:border-b prose-td:border-border/50",
      
      // 画像
      "prose-img:rounded-lg prose-img:shadow-md prose-img:my-6",
      
      // HR
      "prose-hr:border-border prose-hr:my-8",
      
      className
    )}>
      {children}
    </div>
  );
} 