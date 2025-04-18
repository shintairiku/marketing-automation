'use client';

import { useState } from 'react';
import { IoCheckmarkCircle, IoPencil } from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { ArticleOutline } from '@/features/article-generation/types';

interface ArticleOutlineSelectorProps {
  outlines: ArticleOutline[];
  onSelect: (outline: ArticleOutline) => void;
  onEdit: (outline: ArticleOutline) => void;
  isLoading?: boolean;
}

export function ArticleOutlineSelector({
  outlines,
  onSelect,
  onEdit,
  isLoading = false,
}: ArticleOutlineSelectorProps) {
  const [selectedOutlineId, setSelectedOutlineId] = useState<string | null>(null);

  const handleSelect = (outline: ArticleOutline) => {
    setSelectedOutlineId(outline.id);
    onSelect(outline);
  };

  return (
    <div className="w-full space-y-6">
      <h2 className="text-xl font-semibold">記事構成案を選択</h2>
      <p className="text-sm text-muted-foreground">
        以下の候補から最適な記事構成を選択してください。必要に応じて編集も可能です。
      </p>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {outlines.map((outline) => (
          <div
            key={outline.id}
            className={`rounded-lg border p-4 transition-all hover:border-primary cursor-pointer ${
              selectedOutlineId === outline.id
                ? 'border-primary bg-primary/10'
                : 'border-border'
            }`}
            onClick={() => handleSelect(outline)}
          >
            <div className="flex items-start justify-between">
              <h3 className="text-lg font-medium">{outline.title}</h3>
              {selectedOutlineId === outline.id && (
                <IoCheckmarkCircle className="mt-1 text-indigo-500" size={20} />
              )}
            </div>

            <div className="mt-3 space-y-2">
              {outline.sections.map((section) => (
                <div key={section.id} className="pl-3 text-sm">
                  {section.level === 'h2' && (
                    <div className="font-medium text-muted-foreground">{section.title}</div>
                  )}
                  {section.level === 'h3' && (
                    <div className="pl-4 text-muted-foreground">・{section.title}</div>
                  )}
                  {section.level === 'h4' && (
                    <div className="pl-8 text-gray-500">- {section.title}</div>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-4 flex justify-end">
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(outline);
                }}
                disabled={isLoading}
              >
                <IoPencil className="mr-1" size={16} /> 編集
              </Button>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-center pt-4">
        <Button
          variant="sexy"
          disabled={!selectedOutlineId || isLoading}
          onClick={() => {
            const selectedOutline = outlines.find((o) => o.id === selectedOutlineId);
            if (selectedOutline) {
              onSelect(selectedOutline);
            }
          }}
        >
          選択した構成で記事を生成
        </Button>
      </div>
    </div>
  );
}
