'use client';

import React, { useEffect,useState } from 'react';
import { BookOpen, Check } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';

interface Heading {
  id: string;
  level: number; // 1-6 (h1-h6)
  text: string;
  anchor: string; // URLフラグメント用
}

interface TableOfContentsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onInsertToc: (tocHtml: string) => void;
  htmlContent: string; // 全記事のHTMLコンテンツ
}

interface TocSettings {
  includedLevels: Set<number>;
  showNumbers: boolean;
  showIndentation: boolean;
  title: string;
}

export default function TableOfContentsDialog({
  isOpen,
  onClose,
  onInsertToc,
  htmlContent
}: TableOfContentsDialogProps) {
  const [headings, setHeadings] = useState<Heading[]>([]);
  const [settings, setSettings] = useState<TocSettings>({
    includedLevels: new Set([1, 2, 3]),
    showNumbers: true,
    showIndentation: true,
    title: '目次'
  });

  // HTMLから見出しを抽出
  useEffect(() => {
    if (!htmlContent) return;

    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, 'text/html');
    const headingElements = doc.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    const extractedHeadings: Heading[] = Array.from(headingElements).map((element, index) => {
      const level = parseInt(element.tagName.charAt(1));
      const text = element.textContent?.trim() || '';
      const anchor = `heading-${index + 1}`;
      
      return {
        id: `${level}-${index}`,
        level,
        text,
        anchor
      };
    });

    setHeadings(extractedHeadings);
  }, [htmlContent]);

  // フィルタリングされた見出し
  const filteredHeadings = headings.filter(heading => 
    settings.includedLevels.has(heading.level)
  );

  // 目次HTMLを生成
  const generateTocHtml = (): string => {
    if (filteredHeadings.length === 0) return '';

    let tocHtml = `<div class="table-of-contents">
  <h3 class="toc-title">${settings.title}</h3>
  <nav class="toc-nav">`;

    if (settings.showNumbers) {
      tocHtml += `<ol class="toc-list ${settings.showIndentation ? 'toc-indented' : ''}">`;
    } else {
      tocHtml += `<ul class="toc-list ${settings.showIndentation ? 'toc-indented' : ''}">`;
    }

    filteredHeadings.forEach(heading => {
      const indentClass = settings.showIndentation ? `toc-level-${heading.level}` : '';
      tocHtml += `
      <li class="toc-item ${indentClass}">
        <a href="#${heading.anchor}" class="toc-link">
          ${heading.text}
        </a>
      </li>`;
    });

    tocHtml += settings.showNumbers ? '</ol>' : '</ul>';
    tocHtml += `
  </nav>
</div>

<style>
.table-of-contents {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
}

.toc-title {
  margin: 0 0 16px 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 8px;
}

.toc-nav {
  font-size: 0.95rem;
}

.toc-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.toc-list ol,
.toc-list ul {
  margin: 4px 0;
  padding-left: 20px;
}

.toc-item {
  margin: 6px 0;
  line-height: 1.5;
}

.toc-indented .toc-level-1 { margin-left: 0; }
.toc-indented .toc-level-2 { margin-left: 20px; }
.toc-indented .toc-level-3 { margin-left: 40px; }
.toc-indented .toc-level-4 { margin-left: 60px; }
.toc-indented .toc-level-5 { margin-left: 80px; }
.toc-indented .toc-level-6 { margin-left: 100px; }

.toc-link {
  color: #3b82f6;
  text-decoration: none;
  transition: color 0.2s;
  display: block;
  padding: 2px 0;
}

.toc-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}
</style>`;

    return tocHtml;
  };

  // 見出しレベルの切り替え
  const toggleLevel = (level: number) => {
    const newLevels = new Set(settings.includedLevels);
    if (newLevels.has(level)) {
      newLevels.delete(level);
    } else {
      newLevels.add(level);
    }
    setSettings({ ...settings, includedLevels: newLevels });
  };

  // 目次を挿入
  const handleInsert = () => {
    const tocHtml = generateTocHtml();
    onInsertToc(tocHtml);
    onClose();
  };

  const headingCounts = headings.reduce((counts, heading) => {
    counts[heading.level] = (counts[heading.level] || 0) + 1;
    return counts;
  }, {} as Record<number, number>);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader className="space-y-3">
          <DialogTitle className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <BookOpen className="w-5 h-5" />
            目次を追加
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          {/* 設定パネル */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">目次の設定</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 見出しレベル選択 */}
                <div>
                  <Label className="text-sm font-medium mb-3 block">含める見出しレベル</Label>
                  <div className="space-y-2">
                    {[1, 2, 3, 4, 5, 6].map(level => (
                      <div key={level} className="flex items-center space-x-3">
                        <Checkbox
                          id={`level-${level}`}
                          checked={settings.includedLevels.has(level)}
                          onCheckedChange={() => toggleLevel(level)}
                          disabled={!headingCounts[level]}
                        />
                        <Label 
                          htmlFor={`level-${level}`}
                          className={`text-sm ${!headingCounts[level] ? 'text-gray-400' : ''}`}
                        >
                          H{level} ({headingCounts[level] || 0}個)
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                <Separator />

                {/* スタイル設定 */}
                <div>
                  <Label className="text-sm font-medium mb-3 block">スタイル設定</Label>
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3">
                      <Checkbox
                        id="show-numbers"
                        checked={settings.showNumbers}
                        onCheckedChange={(checked) => 
                          setSettings({ ...settings, showNumbers: !!checked })
                        }
                      />
                      <Label htmlFor="show-numbers" className="text-sm">
                        番号を表示
                      </Label>
                    </div>
                    <div className="flex items-center space-x-3">
                      <Checkbox
                        id="show-indentation"
                        checked={settings.showIndentation}
                        onCheckedChange={(checked) => 
                          setSettings({ ...settings, showIndentation: !!checked })
                        }
                      />
                      <Label htmlFor="show-indentation" className="text-sm">
                        階層をインデントで表示
                      </Label>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* プレビューパネル */}
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">プレビュー</CardTitle>
              </CardHeader>
              <CardContent>
                {filteredHeadings.length > 0 ? (
                  <div 
                    className="border rounded-lg p-4 bg-white"
                    dangerouslySetInnerHTML={{ __html: generateTocHtml() }}
                  />
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <BookOpen className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p className="text-sm">表示する見出しがありません</p>
                    <p className="text-xs mt-1">見出しレベルを選択してください</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* アクションボタン */}
        <div className="flex justify-end gap-3 mt-6 pt-6 border-t">
          <Button variant="outline" onClick={onClose}>
            キャンセル
          </Button>
          <Button 
            onClick={handleInsert} 
            disabled={filteredHeadings.length === 0}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Check className="w-4 h-4 mr-2" />
            目次を挿入
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}