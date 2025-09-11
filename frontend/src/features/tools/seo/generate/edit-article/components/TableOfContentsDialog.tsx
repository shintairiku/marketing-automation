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
  onInsertToc: (tocHtml: string, updatedHtmlContent: string) => void;
  htmlContent: string; // 全記事のHTMLコンテンツ
}

interface TocSettings {
  includedLevels: Set<number>;
  showNumbers: boolean;
  showIndentation: boolean;
  title: string;
}

// シンプルな連番IDを生成する関数
const generateSafeId = (text: string, index: number): string => {
  return `heading-${index + 1}`;
};

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

  // HTMLから見出しを抽出（既存の目次領域は除外）
  useEffect(() => {
    if (!htmlContent) return;

    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, 'text/html');
    const headingElements = doc.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    // 既存の目次の見出しをカウントに含めない
    const validHeadingElements = Array.from(headingElements).filter(el => {
      // data-toc 配下は除外
      if (el.closest('[data-toc="true"]')) return false;
      // nav（アンカー一覧）を内包するコンテナ内の見出しも除外（旧TOC対策）
      const containerDiv = el.closest('div');
      if (containerDiv && containerDiv.querySelector('nav a[href^="#"]')) return false;
      return true;
    });

    const extractedHeadings: Heading[] = validHeadingElements.map((element, index) => {
      const level = parseInt(element.tagName.charAt(1));
      const text = element.textContent?.trim() || '';
      const anchor = generateSafeId(text, index);
      
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

  // 目次HTMLを生成（シンプルな生HTML）
  const generateTocHtml = (): string => {
    if (filteredHeadings.length === 0) return '';

    // data-toc マーカーで将来の解析時にこの領域を簡単に除外できるようにする
    let tocHtml = `<div data-toc="true">
<h3>${settings.title}</h3>
<nav>`;

    if (settings.showNumbers) {
      tocHtml += '<ol>';
    } else {
      tocHtml += '<ul>';
    }

    filteredHeadings.forEach(heading => {
      tocHtml += `<li><a href="#${heading.anchor}">${heading.text}</a></li>`;
    });

    tocHtml += settings.showNumbers ? '</ol>' : '</ul>';
    tocHtml += `</nav>
</div>`;

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

  // 記事HTMLに見出しIDを自動設定する関数
  const addHeadingIds = (html: string): string => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const headingElements = doc.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    // 既存目次配下はスキップ、旧TOCと推測されるものもスキップ
    const validHeadingElements = Array.from(headingElements).filter(el => {
      if (el.closest('[data-toc="true"]')) return false;
      const containerDiv = el.closest('div');
      if (containerDiv && containerDiv.querySelector('nav a[href^="#"]')) return false;
      return true;
    });

    validHeadingElements.forEach((element, index) => {
      const text = element.textContent?.trim() || '';
      const anchor = generateSafeId(text, index);
      element.setAttribute('id', anchor);
    });
    
    return doc.body.innerHTML;
  };

  // 目次を挿入
  const handleInsert = () => {
    const tocHtml = generateTocHtml();
    const updatedHtmlContent = addHeadingIds(htmlContent);
    onInsertToc(tocHtml, updatedHtmlContent);
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
