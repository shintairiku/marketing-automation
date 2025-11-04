'use client';

import React from 'react';
import { Check, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface UnifiedDiffLine {
  type: 'unchanged' | 'change';
  content?: string;
  line_number?: number;
  change_id?: string;
  old_lines?: string[];
  new_lines?: string[];
  approved?: boolean;
}

interface UnifiedDiffViewerProps {
  lines: UnifiedDiffLine[];
  onApprove: (changeId: string) => void;
  onReject: (changeId: string) => void;
}

export default function UnifiedDiffViewer({ lines, onApprove, onReject }: UnifiedDiffViewerProps) {
  return (
    <ScrollArea className="h-full">
      <div className="font-mono text-sm">
        {lines.map((line, index) => {
          if (line.type === 'unchanged') {
            return (
              <div key={index} className="flex hover:bg-gray-50">
                <div className="w-12 text-right pr-4 text-gray-400 select-none flex-shrink-0">
                  {line.line_number}
                </div>
                <div className="flex-1 px-4 py-1 whitespace-pre-wrap break-words">
                  <div className="diff-html" dangerouslySetInnerHTML={{ __html: line.content || '' }} />
                </div>
              </div>
            );
          } else if (line.type === 'change') {
            const isApproved = line.approved;
            return (
              <div key={index} className="border-l-4 border-blue-500 my-2">
                {/* 変更ヘッダー */}
                <div className="bg-blue-50 px-4 py-2 flex items-center justify-between">
                  <div className="text-xs text-blue-700 font-medium">
                    変更 (行 {line.line_number})
                  </div>
                  <div className="flex gap-2">
                    {isApproved ? (
                      <div className="flex items-center gap-1 text-green-600 text-xs font-medium">
                        <Check className="h-3 w-3" />
                        承認済み
                      </div>
                    ) : (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => line.change_id && onReject(line.change_id)}
                          className="h-7 text-xs"
                        >
                          <X className="h-3 w-3 mr-1" />
                          拒否
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => line.change_id && onApprove(line.change_id)}
                          className="h-7 text-xs"
                        >
                          <Check className="h-3 w-3 mr-1" />
                          承認
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                {/* 削除された行（赤） */}
                {line.old_lines && line.old_lines.length > 0 && (
                  <div className="bg-red-50">
                    {line.old_lines.map((oldLine, oldIdx) => (
                      <div key={`old-${oldIdx}`} className="flex">
                        <div className="w-12 text-right pr-4 text-gray-400 bg-red-100 select-none flex-shrink-0">
                          -
                        </div>
                        <div className="flex-1 px-4 py-1 bg-red-50 text-red-800 whitespace-pre-wrap break-words">
                          <div className="diff-html" dangerouslySetInnerHTML={{ __html: oldLine }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 追加された行（緑） */}
                {line.new_lines && line.new_lines.length > 0 && (
                  <div className="bg-green-50">
                    {line.new_lines.map((newLine, newIdx) => (
                      <div key={`new-${newIdx}`} className="flex">
                        <div className="w-12 text-right pr-4 text-gray-400 bg-green-100 select-none flex-shrink-0">
                          +
                        </div>
                        <div className="flex-1 px-4 py-1 bg-green-50 text-green-800 whitespace-pre-wrap break-words">
                          <div className="diff-html" dangerouslySetInnerHTML={{ __html: newLine }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          }

          return null;
        })}
      </div>
      <style jsx global>{`
        .diff-html figure {
          margin: 0.75rem auto;
          max-width: 340px !important;
          width: 100%;
          text-align: center;
        }

        .diff-html figure > img,
        .diff-html img {
          display: block;
          width: 100% !important;
          max-width: 320px !important;
          height: auto !important;
          margin: 0.75rem auto;
          border-radius: 1rem;
          box-shadow: 0 12px 26px -14px rgba(15, 23, 42, 0.5);
        }

        @media (max-width: 768px) {
          .diff-html figure {
            max-width: min(92vw, 300px) !important;
          }

          .diff-html figure > img,
          .diff-html img {
            max-width: min(90vw, 280px) !important;
            margin: 0.75rem auto;
          }
        }

        .diff-html figcaption {
          margin-top: 0.75rem;
          font-size: 0.85rem;
          color: #475569;
        }
      `}</style>
    </ScrollArea>
  );
}
