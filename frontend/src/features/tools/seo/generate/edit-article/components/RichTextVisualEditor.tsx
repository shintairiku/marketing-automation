'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  Bold,
  Eraser,
  Heading2,
  Heading3,
  Italic,
  Link2,
  List,
  ListOrdered,
  Quote,
  Strikethrough,
  Underline,
  Undo,
  Redo,
} from 'lucide-react';

import { cn } from '@/utils/cn';

interface RichTextVisualEditorProps {
  value: string;
  onChange: (nextHtml: string) => void;
  className?: string;
  placeholder?: string;
}

interface ToolbarButton {
  key: string;
  icon: React.ReactNode;
  label: string;
  command?: string;
  commandValue?: string;
  onClick?: () => void;
}

const DEFAULT_PLACEHOLDER = 'ここにコンテンツを入力してください';

const isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined';

const RichTextVisualEditor: React.FC<RichTextVisualEditorProps> = ({
  value,
  onChange,
  className,
  placeholder = DEFAULT_PLACEHOLDER,
}) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const [isFocused, setIsFocused] = useState(false);

  // 同期的にHTMLを反映
  useEffect(() => {
    if (!editorRef.current) return;
    const editor = editorRef.current;
    const sanitized = value && value.trim().length > 0 ? value : '<p><br></p>';
    if (editor.innerHTML !== sanitized) {
      editor.innerHTML = sanitized;
    }
  }, [value]);

  const emitChange = () => {
    if (!editorRef.current) return;
    let html = editorRef.current.innerHTML;
    // ブラウザによっては <div><br></div> が生成されるため空扱いにする
    if (html === '<div><br></div>' || html === '<p><br></p>' || html === '<br>') {
      html = '';
    }
    onChange(html);
  };

  const execute = (command: string, commandValue?: string) => {
    if (!isBrowser || !editorRef.current) return;
    editorRef.current.focus();
    try {
      document.execCommand(command, false, commandValue ?? undefined);
    } catch (error) {
      console.error('Failed to execute command', command, error);
    }
    emitChange();
  };

  const handleCreateLink = () => {
    if (!isBrowser || !editorRef.current) return;
    const url = window.prompt('リンク先のURLを入力してください');
    if (!url) {
      execute('unlink');
      return;
    }
    editorRef.current.focus();
    document.execCommand('createLink', false, url);
    emitChange();
  };

  const toolbarButtons: ToolbarButton[] = [
    { key: 'bold', icon: <Bold className="h-4 w-4" />, label: '太字', command: 'bold' },
    { key: 'italic', icon: <Italic className="h-4 w-4" />, label: '斜体', command: 'italic' },
    { key: 'underline', icon: <Underline className="h-4 w-4" />, label: '下線', command: 'underline' },
    { key: 'strike', icon: <Strikethrough className="h-4 w-4" />, label: '打ち消し線', command: 'strikeThrough' },
    { key: 'h2', icon: <Heading2 className="h-4 w-4" />, label: '見出し2', command: 'formatBlock', commandValue: 'H2' },
    { key: 'h3', icon: <Heading3 className="h-4 w-4" />, label: '見出し3', command: 'formatBlock', commandValue: 'H3' },
    { key: 'ul', icon: <List className="h-4 w-4" />, label: '箇条書き', command: 'insertUnorderedList' },
    { key: 'ol', icon: <ListOrdered className="h-4 w-4" />, label: '番号付き', command: 'insertOrderedList' },
    { key: 'quote', icon: <Quote className="h-4 w-4" />, label: '引用', command: 'formatBlock', commandValue: 'BLOCKQUOTE' },
    { key: 'link', icon: <Link2 className="h-4 w-4" />, label: 'リンク', onClick: handleCreateLink },
    { key: 'clear', icon: <Eraser className="h-4 w-4" />, label: '書式クリア', command: 'removeFormat' },
    { key: 'undo', icon: <Undo className="h-4 w-4" />, label: '元に戻す', command: 'undo' },
    { key: 'redo', icon: <Redo className="h-4 w-4" />, label: 'やり直す', command: 'redo' },
  ];

  return (
    <div className={cn('flex flex-col border border-gray-200 rounded-lg bg-white shadow-sm', className)}>
      <div className="flex flex-wrap gap-1 border-b border-gray-200 bg-gray-50 px-3 py-2">
        {toolbarButtons.map((button) => {
          const handleMouseDown = (event: React.MouseEvent<HTMLButtonElement>) => {
            event.preventDefault();
            event.stopPropagation();
            if (button.onClick) {
              button.onClick();
              return;
            }
            if (button.command) {
              execute(button.command, button.commandValue);
            }
          };

          return (
            <button
              key={button.key}
              type="button"
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-white px-2 py-1 text-sm text-gray-600 shadow-sm transition-colors hover:bg-purple-50 hover:text-purple-600 focus:outline-none focus:ring-2 focus:ring-purple-500"
              onMouseDown={handleMouseDown}
              aria-label={button.label}
            >
              {button.icon}
            </button>
          );
        })}
      </div>

      <div className="relative">
        <div
          ref={editorRef}
          className={cn(
            'prose prose-base prose-gray max-w-none min-h-[420px] resize-vertical overflow-auto p-6 focus:outline-none',
            isFocused ? 'ring-2 ring-purple-500 ring-offset-0' : ''
          )}
          contentEditable
          suppressContentEditableWarning
          onInput={emitChange}
          onBlur={() => setIsFocused(false)}
          onFocus={() => setIsFocused(true)}
          data-placeholder={placeholder}
        />
        {(!value || value.trim().length === 0) && !isFocused && (
          <div className="pointer-events-none absolute left-6 top-6 text-sm text-gray-400">
            {placeholder}
          </div>
        )}
      </div>
    </div>
  );
};

export default RichTextVisualEditor;
