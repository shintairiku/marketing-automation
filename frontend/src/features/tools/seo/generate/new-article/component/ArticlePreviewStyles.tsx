'use client';

import { ReactNode } from 'react';

interface ArticlePreviewStylesProps {
  children: ReactNode;
  isFullscreen?: boolean;
}

export default function ArticlePreviewStyles({ children, isFullscreen = false }: ArticlePreviewStylesProps) {
  return (
    <div className={`prose prose-gray max-w-none ${isFullscreen ? 'prose-lg' : ''} article-preview-content`}>
      <style jsx>{`
        .prose {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          line-height: 1.75;
          color: #374151;
        }
        
        .prose h1 {
          font-size: ${isFullscreen ? '3rem' : '2.25rem'};
          font-weight: 900;
          margin-bottom: ${isFullscreen ? '2rem' : '1rem'};
          margin-top: ${isFullscreen ? '0' : '2rem'};
          color: #111827;
          line-height: 1.1;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          letter-spacing: -0.02em;
        }
        
        .prose h2 {
          font-size: ${isFullscreen ? '2.25rem' : '1.875rem'};
          font-weight: 800;
          margin-bottom: ${isFullscreen ? '1.5rem' : '0.75rem'};
          margin-top: ${isFullscreen ? '3rem' : '1.5rem'};
          color: #1f2937;
          line-height: 1.2;
          border-bottom: 3px solid #e5e7eb;
          padding-bottom: 0.5rem;
          letter-spacing: -0.01em;
        }
        
        .prose h3 {
          font-size: ${isFullscreen ? '1.875rem' : '1.5rem'};
          font-weight: 700;
          margin-bottom: ${isFullscreen ? '1rem' : '0.5rem'};
          margin-top: ${isFullscreen ? '2rem' : '1.25rem'};
          color: #374151;
          line-height: 1.3;
          position: relative;
          padding-left: 1rem;
        }
        
        .prose h3:before {
          content: '';
          position: absolute;
          left: 0;
          top: 50%;
          transform: translateY(-50%);
          width: 4px;
          height: 60%;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 2px;
        }
        
        .prose h4 {
          font-size: ${isFullscreen ? '1.5rem' : '1.25rem'};
          font-weight: 600;
          margin-bottom: 0.75rem;
          margin-top: 1.5rem;
          color: #4b5563;
          line-height: 1.4;
        }
        
        .prose p {
          margin-bottom: ${isFullscreen ? '1.5rem' : '1rem'};
          line-height: ${isFullscreen ? '1.8' : '1.7'};
          color: #374151;
          font-size: ${isFullscreen ? '1.125rem' : '1rem'};
          text-align: justify;
        }
        
        .prose p:first-of-type {
          font-size: ${isFullscreen ? '1.25rem' : '1.125rem'};
          font-weight: 500;
          color: #1f2937;
          line-height: 1.6;
        }
        
        .prose ul, .prose ol {
          margin-bottom: ${isFullscreen ? '1.5rem' : '1rem'};
          padding-left: ${isFullscreen ? '2rem' : '1.5rem'};
        }
        
        .prose li {
          margin-bottom: ${isFullscreen ? '0.75rem' : '0.5rem'};
          line-height: ${isFullscreen ? '1.7' : '1.6'};
          font-size: ${isFullscreen ? '1.125rem' : '1rem'};
          position: relative;
        }
        
        .prose ul li:before {
          content: '•';
          color: #667eea;
          font-weight: bold;
          position: absolute;
          left: -1rem;
          font-size: 1.2em;
        }
        
        .prose strong {
          font-weight: 700;
          color: #111827;
          background: linear-gradient(135deg, #fbbf24, #f59e0b);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        
        .prose em {
          font-style: italic;
          color: #6b7280;
          font-weight: 500;
        }
        
        .prose blockquote {
          border-left: 4px solid #667eea;
          padding-left: ${isFullscreen ? '2rem' : '1rem'};
          margin: ${isFullscreen ? '2.5rem 0' : '1.5rem 0'};
          font-style: italic;
          color: #4b5563;
          background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
          padding: ${isFullscreen ? '2rem' : '1rem'};
          border-radius: 0.75rem;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          position: relative;
          font-size: ${isFullscreen ? '1.125rem' : '1rem'};
        }
        
        .prose blockquote:before {
          content: '"';
          position: absolute;
          top: -10px;
          left: 20px;
          font-size: 4rem;
          color: #667eea;
          opacity: 0.3;
          font-family: serif;
        }
        
        .prose code {
          background: linear-gradient(135deg, #fef3c7, #fed7aa);
          color: #dc2626;
          padding: 0.25rem 0.5rem;
          border-radius: 0.375rem;
          font-size: ${isFullscreen ? '1rem' : '0.875rem'};
          font-family: 'JetBrains Mono', 'Monaco', 'Consolas', monospace;
          font-weight: 600;
          border: 1px solid #fed7aa;
        }
        
        .prose pre {
          background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
          color: #e2e8f0;
          padding: ${isFullscreen ? '2rem' : '1rem'};
          border-radius: 0.75rem;
          overflow-x: auto;
          margin: ${isFullscreen ? '2rem 0' : '1rem 0'};
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
          border: 1px solid #475569;
        }
        
        .prose pre code {
          background: transparent;
          color: inherit;
          padding: 0;
          border-radius: 0;
          border: none;
          font-size: ${isFullscreen ? '1rem' : '0.875rem'};
        }
        
        .prose a {
          color: #667eea !important;
          text-decoration: none !important;
          font-weight: 600 !important;
          background: linear-gradient(135deg, #667eea, #764ba2) !important;
          -webkit-background-clip: text !important;
          -webkit-text-fill-color: transparent !important;
          background-clip: text !important;
          border-bottom: 2px solid transparent !important;
          border-image: linear-gradient(135deg, #667eea, #764ba2) 1 !important;
          transition: all 0.3s ease !important;
          position: relative !important;
        }
        
        .prose a:hover {
          border-bottom: 2px solid #667eea !important;
          transform: translateY(-1px) !important;
        }
        
        /* 追加のリンクスタイル - 確実に適用するため */
        .article-preview-content a {
          color: #667eea !important;
          text-decoration: none !important;
          font-weight: 600 !important;
          background: linear-gradient(135deg, #667eea, #764ba2) !important;
          -webkit-background-clip: text !important;
          -webkit-text-fill-color: transparent !important;
          background-clip: text !important;
          border-bottom: 2px solid transparent !important;
          border-image: linear-gradient(135deg, #667eea, #764ba2) 1 !important;
          transition: all 0.3s ease !important;
          position: relative !important;
        }
        
        .article-preview-content a:hover {
          border-bottom: 2px solid #667eea !important;
          transform: translateY(-1px) !important;
        }
        
        .prose img {
          border-radius: 0.75rem;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15);
          margin: ${isFullscreen ? '2rem auto' : '1rem auto'};
          max-width: 100%;
          height: auto;
        }
        
        .prose table {
          width: 100%;
          border-collapse: collapse;
          margin: ${isFullscreen ? '2rem 0' : '1rem 0'};
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          border-radius: 0.5rem;
          overflow: hidden;
        }
        
        .prose th, .prose td {
          padding: ${isFullscreen ? '1rem' : '0.75rem'};
          text-align: left;
          border-bottom: 1px solid #e5e7eb;
        }
        
        .prose th {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          font-weight: 700;
          font-size: ${isFullscreen ? '1rem' : '0.875rem'};
        }
        
        .prose tr:hover {
          background-color: #f9fafb;
        }
        
        /* セクション区切り */
        .prose hr {
          border: none;
          height: 2px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          margin: ${isFullscreen ? '3rem 0' : '2rem 0'};
          border-radius: 1px;
          opacity: 0.3;
        }
        
        /* フルスクリーン時の特別なスタイリング */
        ${isFullscreen ? `
          .prose {
            max-width: 4xl;
            margin: 0 auto;
            padding: 3rem 2rem;
            background: white;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15);
            border-radius: 1rem;
            position: relative;
          }
          
          .prose:before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 1rem 1rem 0 0;
          }
        ` : ''}
      `}</style>
      {children}
    </div>
  );
}