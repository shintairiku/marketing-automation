'use client';

import { useEffect, useState } from 'react';
import { IoAdd, IoRemove, IoSave } from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArticleOutline, ArticleSection } from '@/features/article-generation/types';

interface ArticleOutlineEditorProps {
  outline: ArticleOutline;
  onSave: (outline: ArticleOutline) => void;
  onCancel: () => void;
}

export function ArticleOutlineEditor({ outline, onSave, onCancel }: ArticleOutlineEditorProps) {
  const [editedOutline, setEditedOutline] = useState<ArticleOutline>({ ...outline });

  useEffect(() => {
    setEditedOutline({ ...outline });
  }, [outline]);

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditedOutline({
      ...editedOutline,
      title: e.target.value,
    });
  };

  const handleSectionTitleChange = (sectionId: string, value: string) => {
    setEditedOutline({
      ...editedOutline,
      sections: editedOutline.sections.map((section) =>
        section.id === sectionId ? { ...section, title: value } : section
      ),
    });
  };

  const handleSectionLevelChange = (sectionId: string, level: 'h2' | 'h3' | 'h4') => {
    setEditedOutline({
      ...editedOutline,
      sections: editedOutline.sections.map((section) =>
        section.id === sectionId ? { ...section, level } : section
      ),
    });
  };

  const addSection = (afterSectionId: string) => {
    const index = editedOutline.sections.findIndex((s) => s.id === afterSectionId);
    const newSection: ArticleSection = {
      id: `new-section-${Date.now()}`,
      level: 'h2',
      title: '新しいセクション',
    };

    const updatedSections = [...editedOutline.sections];
    updatedSections.splice(index + 1, 0, newSection);

    setEditedOutline({
      ...editedOutline,
      sections: updatedSections,
    });
  };

  const removeSection = (sectionId: string) => {
    if (editedOutline.sections.length <= 1) {
      return; // 少なくとも1つのセクションは残す
    }

    setEditedOutline({
      ...editedOutline,
      sections: editedOutline.sections.filter((s) => s.id !== sectionId),
    });
  };

  return (
    <div className="w-full space-y-6">
      <div>
        <label htmlFor="title" className="block text-sm font-medium mb-1">
          記事タイトル
        </label>
        <Input
          id="title"
          value={editedOutline.title}
          onChange={handleTitleChange}
          className="w-full"
        />
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-medium">セクション構成</h3>
        {editedOutline.sections.map((section, index) => (
          <div key={section.id} className="rounded-md border border-gray-700 p-4">
            <div className="flex items-center gap-3">
              <select
                value={section.level}
                onChange={(e) => handleSectionLevelChange(section.id, e.target.value as 'h2' | 'h3' | 'h4')}
                className="flex h-9 w-24 rounded-md bg-black px-3 py-1 text-sm transition-colors border border-zinc-800"
              >
                <option value="h2">H2</option>
                <option value="h3">H3</option>
                <option value="h4">H4</option>
              </select>
              <Input
                value={section.title}
                onChange={(e) => handleSectionTitleChange(section.id, e.target.value)}
                className="flex-1"
              />
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => addSection(section.id)}
                  title="セクションを追加"
                  type="button"
                >
                  <IoAdd size={18} />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeSection(section.id)}
                  title="セクションを削除"
                  type="button"
                  className="text-red-500 hover:text-red-400"
                  disabled={editedOutline.sections.length <= 1}
                >
                  <IoRemove size={18} />
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <Button variant="outline" onClick={onCancel}>
          キャンセル
        </Button>
        <Button 
          variant="secondary" 
          onClick={() => onSave(editedOutline)}
        >
          <IoSave className="mr-2" size={18} />
          保存
        </Button>
      </div>
    </div>
  );
}
