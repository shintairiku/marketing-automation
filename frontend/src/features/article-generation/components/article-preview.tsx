'use client';

import { useState } from 'react';
import { IoCopy, IoDownload, IoEllipsisVertical } from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/components/ui/use-toast';
import { GeneratedArticle } from '@/features/article-generation/types';

interface ArticlePreviewProps {
  article: GeneratedArticle;
  onStartChat: () => void;
}

export function ArticlePreview({ article, onStartChat }: ArticlePreviewProps) {
  const [activeTab, setActiveTab] = useState<'preview' | 'html' | 'markdown'>('preview');
  const [showMetaDescription, setShowMetaDescription] = useState(false);

  // HTMLフォーマットでの記事を生成
  const generateHtml = () => {
    let html = `<!DOCTYPE html>\n<html lang="ja">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <meta name="description" content="${article.metaDescription}">\n  <title>${article.title}</title>\n</head>\n<body>\n  <article>\n    <h1>${article.title}</h1>\n`;

    article.sections.forEach((section) => {
      if (section.level === 'h2') {
        html += `    <h2>${section.title}</h2>\n`;
      } else if (section.level === 'h3') {
        html += `    <h3>${section.title}</h3>\n`;
      } else if (section.level === 'h4') {
        html += `    <h4>${section.title}</h4>\n`;
      }

      if (section.content) {
        const paragraphs = section.content.split('\n\n');
        paragraphs.forEach((paragraph) => {
          if (paragraph.trim()) {
            html += `    <p>${paragraph.trim()}</p>\n`;
          }
        });
      }
    });

    html += '  </article>\n</body>\n</html>';
    return html;
  };

  // Markdownフォーマットでの記事を生成
  const generateMarkdown = () => {
    let markdown = `# ${article.title}\n\n`;

    article.sections.forEach((section) => {
      if (section.level === 'h2') {
        markdown += `## ${section.title}\n\n`;
      } else if (section.level === 'h3') {
        markdown += `### ${section.title}\n\n`;
      } else if (section.level === 'h4') {
        markdown += `#### ${section.title}\n\n`;
      }

      if (section.content) {
        markdown += `${section.content}\n\n`;
      }
    });

    return markdown;
  };

  // クリップボードにコピー
  const copyToClipboard = (content: string) => {
    navigator.clipboard.writeText(content).then(
      () => {
        toast({
          description: 'クリップボードにコピーしました',
        });
      },
      (err) => {
        toast({
          variant: 'destructive',
          description: 'コピーに失敗しました: ' + err,
        });
      }
    );
  };

  // ファイルとしてダウンロード
  const downloadAsFile = (content: string, fileType: string) => {
    const fileName = `${article.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}`;
    const fileExtension = fileType === 'html' ? 'html' : 'md';
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = `${fileName}.${fileExtension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(href);
  };

  // プレビュー表示
  const renderPreview = () => {
    return (
      <div className="prose prose-invert max-w-none">
        <h1 className="mb-6 text-2xl font-bold">{article.title}</h1>

        {showMetaDescription && (
          <div className="mb-6 rounded-md border border-border bg-muted/30 p-3">
            <p className="text-sm text-muted-foreground">
              <span className="font-semibold">メタディスクリプション:</span> {article.metaDescription}
            </p>
          </div>
        )}

        {article.sections.map((section) => (
          <div key={section.id} className="mb-6">
            {section.level === 'h2' && <h2 className="mt-8 text-xl font-semibold">{section.title}</h2>}
            {section.level === 'h3' && <h3 className="mt-6 text-lg font-medium">{section.title}</h3>}
            {section.level === 'h4' && <h4 className="mt-4 text-base font-medium">{section.title}</h4>}

            {section.content && (
              <div className="mt-3 space-y-4">
                {section.content.split('\n\n').map((paragraph, idx) => (
                  <p key={idx} className="text-muted-foreground">
                    {paragraph}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  // HTML表示
  const renderHtml = () => {
    return <Textarea value={generateHtml()} readOnly className="h-[600px] font-mono text-xs" />;
  };

  // Markdown表示
  const renderMarkdown = () => {
    return <Textarea value={generateMarkdown()} readOnly className="h-[600px] font-mono text-xs" />;
  };

  return (
    <div className="w-full space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={activeTab === 'preview' ? 'default' : 'outline'}
            onClick={() => setActiveTab('preview')}
          >
            プレビュー
          </Button>
          <Button
            size="sm"
            variant={activeTab === 'html' ? 'default' : 'outline'}
            onClick={() => setActiveTab('html')}
          >
            HTML
          </Button>
          <Button
            size="sm"
            variant={activeTab === 'markdown' ? 'default' : 'outline'}
            onClick={() => setActiveTab('markdown')}
          >
            Markdown
          </Button>
        </div>

        <div className="flex gap-2">
          {activeTab === 'preview' ? (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowMetaDescription(!showMetaDescription)}
            >
              {showMetaDescription ? 'メタ情報を隠す' : 'メタ情報を表示'}
            </Button>
          ) : (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  copyToClipboard(activeTab === 'html' ? generateHtml() : generateMarkdown())
                }
              >
                <IoCopy className="mr-1" size={16} /> コピー
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  downloadAsFile(
                    activeTab === 'html' ? generateHtml() : generateMarkdown(),
                    activeTab
                  )
                }
              >
                <IoDownload className="mr-1" size={16} /> ダウンロード
              </Button>
            </>
          )}

          <Button size="sm" variant="sexy" onClick={onStartChat}>
            チャットで編集
          </Button>
        </div>
      </div>

      <div className="min-h-[600px] rounded-md border border-border bg-background p-6">
        {activeTab === 'preview' && renderPreview()}
        {activeTab === 'html' && renderHtml()}
        {activeTab === 'markdown' && renderMarkdown()}
      </div>
    </div>
  );
}
