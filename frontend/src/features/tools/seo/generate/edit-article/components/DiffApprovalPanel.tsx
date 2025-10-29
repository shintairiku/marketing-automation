'use client';

import React from 'react';
import { Check, X } from 'lucide-react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

interface PendingChange {
  change_id: string;
  old_text: string;
  new_text: string;
  description: string;
  approved: boolean;
}

interface DiffApprovalPanelProps {
  changes: PendingChange[];
  onApprove: (changeId: string) => void;
  onReject: (changeId: string) => void;
  onApproveAll: () => void;
  onRejectAll: () => void;
  onApplyChanges: () => void;
}

export default function DiffApprovalPanel({
  changes,
  onApprove,
  onReject,
  onApproveAll,
  onRejectAll,
  onApplyChanges,
}: DiffApprovalPanelProps) {
  const hasApprovedChanges = changes.some((c) => c.approved);
  const allApproved = changes.every((c) => c.approved);

  return (
    <div className="flex flex-col h-full">
      {/* ヘッダー */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b">
        <div>
          <h3 className="text-lg font-semibold">変更の承認</h3>
          <p className="text-sm text-gray-600">
            {changes.length}件の変更があります。承認または拒否を選択してください。
          </p>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onRejectAll} disabled={changes.length === 0}>
            <X className="h-4 w-4 mr-1" />
            すべて拒否
          </Button>
          <Button variant="outline" size="sm" onClick={onApproveAll} disabled={allApproved || changes.length === 0}>
            <Check className="h-4 w-4 mr-1" />
            すべて承認
          </Button>
          <Button size="sm" onClick={onApplyChanges} disabled={!hasApprovedChanges}>
            変更を適用
          </Button>
        </div>
      </div>

      {/* 変更リスト */}
      <ScrollArea className="flex-1">
        <div className="space-y-6">
          {changes.length === 0 ? (
            <Card className="p-8 text-center">
              <p className="text-gray-500">承認待ちの変更はありません</p>
            </Card>
          ) : (
            changes.map((change, index) => (
              <Card key={change.change_id} className="p-4">
                {/* 変更ヘッダー */}
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="font-medium">変更 #{index + 1}</h4>
                    <p className="text-sm text-gray-600">{change.description}</p>
                  </div>

                  <div className="flex gap-2">
                    {change.approved ? (
                      <div className="flex items-center gap-1 text-green-600 text-sm font-medium">
                        <Check className="h-4 w-4" />
                        承認済み
                      </div>
                    ) : (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onReject(change.change_id)}
                        >
                          <X className="h-4 w-4 mr-1" />
                          拒否
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => onApprove(change.change_id)}
                        >
                          <Check className="h-4 w-4 mr-1" />
                          承認
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                {/* 差分表示 */}
                <div className="border rounded-lg overflow-hidden">
                  <ReactDiffViewer
                    oldValue={change.old_text}
                    newValue={change.new_text}
                    splitView={true}
                    compareMethod={DiffMethod.WORDS}
                    useDarkTheme={false}
                    leftTitle="変更前"
                    rightTitle="変更後"
                    styles={{
                      variables: {
                        light: {
                          diffViewerBackground: '#fff',
                          diffViewerColor: '#212529',
                          addedBackground: '#e6ffed',
                          addedColor: '#24292e',
                          removedBackground: '#ffeef0',
                          removedColor: '#24292e',
                          wordAddedBackground: '#acf2bd',
                          wordRemovedBackground: '#fdb8c0',
                          addedGutterBackground: '#cdffd8',
                          removedGutterBackground: '#ffdce0',
                          gutterBackground: '#f6f8fa',
                          gutterBackgroundDark: '#f3f4f6',
                          highlightBackground: '#fffbdd',
                          highlightGutterBackground: '#fff5b1',
                        },
                      },
                      contentText: {
                        fontSize: '13px',
                        lineHeight: '1.6',
                      },
                    }}
                  />
                </div>
              </Card>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
