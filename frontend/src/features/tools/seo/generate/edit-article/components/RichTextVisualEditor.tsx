'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Bold,
  Eraser,
  Heading2,
  Heading3,
  Heading4,
  Italic,
  Link2,
  List,
  ListOrdered,
  Quote,
  Redo,
  Strikethrough,
  Underline,
  Undo,
} from 'lucide-react';

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
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

// Simple debounce function
function useDebounce<T extends (...args: any[]) => void>(func: T, delay: number): T {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  return useCallback(
    ((...args: any[]) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => func(...args), delay);
    }) as T,
    [func, delay]
  );
}

const RichTextVisualEditor: React.FC<RichTextVisualEditorProps> = ({
  value,
  onChange,
  className,
  placeholder = DEFAULT_PLACEHOLDER,
}) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const [isFocused, setIsFocused] = useState(false);
  const isUpdatingRef = useRef(false);
  const lastValueRef = useRef(value);
  const [activeStates, setActiveStates] = useState<Record<string, boolean>>({});
  const [editorHeight, setEditorHeight] = useState(420);

  // Debounced onChange to reduce frequent updates
  const debouncedOnChange = useDebounce(onChange, 200);

  // Calculate dynamic editor height based on screen size
  const calculateEditorHeight = useCallback(() => {
    if (!isBrowser) return 420;

    const windowHeight = window.innerHeight;
    const toolbarHeight = 52; // Approximate toolbar height
    const headerHeight = 80; // Approximate page header height
    const paddingBuffer = 120; // Buffer for margins and padding

    const availableHeight = windowHeight - headerHeight - toolbarHeight - paddingBuffer;
    const minHeight = 300; // Minimum editor height
    const maxHeight = 800; // Maximum editor height for very tall screens

    return Math.max(minHeight, Math.min(maxHeight, availableHeight));
  }, []);

  // Update editor height on window resize
  useEffect(() => {
    if (!isBrowser) return;

    const updateHeight = () => {
      setEditorHeight(calculateEditorHeight());
    };

    // Set initial height
    updateHeight();

    // Listen for window resize
    window.addEventListener('resize', updateHeight);
    return () => window.removeEventListener('resize', updateHeight);
  }, [calculateEditorHeight]);

  // Check formatting states for active button styling
  const checkActiveStates = useCallback(() => {
    if (!isBrowser || !editorRef.current || !isFocused) return;

    try {
      const states: Record<string, boolean> = {
        bold: document.queryCommandState('bold'),
        italic: document.queryCommandState('italic'),
        underline: document.queryCommandState('underline'),
        strikeThrough: document.queryCommandState('strikeThrough'),
        insertUnorderedList: document.queryCommandState('insertUnorderedList'),
        insertOrderedList: document.queryCommandState('insertOrderedList'),
      };

      // Check for heading types by examining the selection
      const selection = window.getSelection();
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        let element: HTMLElement | null = range.commonAncestorContainer as HTMLElement;

        if (element.nodeType === Node.TEXT_NODE) {
          element = element.parentElement;
          if (!element) return;
        }

        while (element && element !== editorRef.current) {
          const tagName = (element as Element).tagName?.toLowerCase();
          if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) {
            states[tagName] = true;
            break;
          }
          if (tagName === 'blockquote') {
            states.blockquote = true;
            break;
          }
          element = element.parentElement;
          if (!element) break;
        }
      }

      setActiveStates(states);
    } catch (error) {
      console.error('Error checking command states:', error);
    }
  }, [isFocused]);

  // Handle input changes
  const handleInput = useCallback(() => {
    if (!editorRef.current || isUpdatingRef.current) return;

    const currentHtml = editorRef.current.innerHTML;

    // Only emit if content actually changed
    if (currentHtml !== lastValueRef.current) {
      lastValueRef.current = currentHtml;
      debouncedOnChange(currentHtml);
    }

    // Check active states after input
    checkActiveStates();
  }, [debouncedOnChange, checkActiveStates]);

  // Listen for selection changes to update active states
  useEffect(() => {
    if (!isBrowser) return;

    const handleSelectionChange = () => {
      if (isFocused && editorRef.current?.contains(document.activeElement)) {
        checkActiveStates();
      }
    };

    document.addEventListener('selectionchange', handleSelectionChange);
    return () => document.removeEventListener('selectionchange', handleSelectionChange);
  }, [isFocused, checkActiveStates]);

  // Sync external value changes (only when not actively editing)
  useEffect(() => {
    if (!editorRef.current || isUpdatingRef.current) return;

    const editor = editorRef.current;
    const currentHtml = editor.innerHTML;

    // Only update if external value is different and editor is not focused
    if (value !== currentHtml && !isFocused) {
      isUpdatingRef.current = true;
      const sanitized = value && value.trim().length > 0 ? value : '<p><br></p>';
      editor.innerHTML = sanitized;
      lastValueRef.current = sanitized;

      // Reset flag after DOM update
      requestAnimationFrame(() => {
        isUpdatingRef.current = false;
      });
    }
  }, [value, isFocused]);

  const execute = useCallback((command: string, commandValue?: string) => {
    if (!isBrowser || !editorRef.current) return;

    try {
      editorRef.current.focus();
      document.execCommand(command, false, commandValue ?? undefined);
      handleInput(); // Trigger change detection
    } catch (error) {
      console.error('Failed to execute command', command, error);
    }
  }, [handleInput]);

  const handleCreateLink = useCallback(() => {
    if (!isBrowser || !editorRef.current) return;

    const url = window.prompt('リンク先のURLを入力してください');
    if (!url) {
      execute('unlink');
      return;
    }

    execute('createLink', url);
  }, [execute]);

  const handleFocus = useCallback(() => {
    setIsFocused(true);
    // Check active states when focused
    setTimeout(checkActiveStates, 0);
  }, [checkActiveStates]);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
    // Force sync on blur to ensure consistency
    handleInput();
  }, [handleInput]);

  const toolbarButtons: ToolbarButton[] = [
    { key: 'bold', icon: <Bold className="h-4 w-4" />, label: '太字（Ctrl+B）- 選択したテキストを太字にします', command: 'bold' },
    { key: 'italic', icon: <Italic className="h-4 w-4" />, label: '斜体（Ctrl+I）- 選択したテキストを斜体にします', command: 'italic' },
    { key: 'underline', icon: <Underline className="h-4 w-4" />, label: '下線（Ctrl+U）- 選択したテキストに下線を引きます', command: 'underline' },
    { key: 'strike', icon: <Strikethrough className="h-4 w-4" />, label: '打ち消し線 - 選択したテキストに打ち消し線を引きます', command: 'strikeThrough' },
    { key: 'h2', icon: <Heading2 className="h-4 w-4" />, label: '見出し2 - 大見出しを作成します', command: 'formatBlock', commandValue: 'H2' },
    { key: 'h3', icon: <Heading3 className="h-4 w-4" />, label: '見出し3 - 中見出しを作成します', command: 'formatBlock', commandValue: 'H3' },
    { key: 'h4', icon: <Heading4 className="h-4 w-4" />, label: '見出し4 - 小見出しを作成します', command: 'formatBlock', commandValue: 'H4' },
    { key: 'ul', icon: <List className="h-4 w-4" />, label: '箇条書き - 順序なしリストを作成します', command: 'insertUnorderedList' },
    { key: 'ol', icon: <ListOrdered className="h-4 w-4" />, label: '番号付きリスト - 順序ありリストを作成します', command: 'insertOrderedList' },
    { key: 'quote', icon: <Quote className="h-4 w-4" />, label: '引用 - 引用ブロックを作成します', command: 'formatBlock', commandValue: 'BLOCKQUOTE' },
    { key: 'link', icon: <Link2 className="h-4 w-4" />, label: 'リンク（Ctrl+K）- 選択したテキストにリンクを設定します', onClick: handleCreateLink },
    { key: 'clear', icon: <Eraser className="h-4 w-4" />, label: '書式クリア - 選択したテキストの書式をクリアします', command: 'removeFormat' },
    { key: 'undo', icon: <Undo className="h-4 w-4" />, label: '元に戻す（Ctrl+Z）- 直前の操作を取り消します', command: 'undo' },
    { key: 'redo', icon: <Redo className="h-4 w-4" />, label: 'やり直す（Ctrl+Y）- 取り消した操作をやり直します', command: 'redo' },
  ];

  return (
    <TooltipProvider>
      <div className={cn('flex flex-col border border-gray-200 rounded-lg bg-white shadow-sm', className)}>
        <div className="flex flex-wrap gap-1 border-b border-gray-200 bg-gray-50 px-3 py-2">
          {toolbarButtons.map((button) => {
            const handleMouseDown = (event: React.MouseEvent<HTMLButtonElement>) => {
              event.preventDefault(); // Prevent focus loss
              if (button.onClick) {
                button.onClick();
              } else if (button.command) {
                execute(button.command, button.commandValue);
              }
            };

            // Determine if button is active
            const isActive = (() => {
              switch (button.key) {
                case 'bold':
                  return activeStates.bold;
                case 'italic':
                  return activeStates.italic;
                case 'underline':
                  return activeStates.underline;
                case 'strike':
                  return activeStates.strikeThrough;
                case 'h2':
                  return activeStates.h2;
                case 'h3':
                  return activeStates.h3;
                case 'h4':
                  return activeStates.h4;
                case 'ul':
                  return activeStates.insertUnorderedList;
                case 'ol':
                  return activeStates.insertOrderedList;
                case 'quote':
                  return activeStates.blockquote;
                default:
                  return false;
              }
            })();

            return (
              <Tooltip key={button.key}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className={cn(
                      "inline-flex items-center justify-center rounded-md border border-transparent px-2 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500",
                      isActive
                        ? "bg-purple-100 text-purple-700 border-purple-200 hover:bg-purple-200"
                        : "bg-white text-gray-600 hover:bg-purple-50 hover:text-purple-600"
                    )}
                    onMouseDown={handleMouseDown}
                    aria-label={button.label}
                    aria-pressed={isActive}
                  >
                    {button.icon}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-xs">
                  <p className="text-xs">{button.label}</p>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>

        <div className="relative">
          <div
            ref={editorRef}
            className={cn(
              'prose prose-base prose-gray max-w-none overflow-y-auto p-6 focus:outline-none',
              isFocused ? 'ring-2 ring-purple-500 ring-offset-0' : ''
            )}
            style={{ height: `${editorHeight}px` }}
            contentEditable
            suppressContentEditableWarning
            onInput={handleInput}
            onFocus={handleFocus}
            onBlur={handleBlur}
            data-placeholder={placeholder}
          />
          {(!value || value.trim().length === 0) && !isFocused && (
            <div className="pointer-events-none absolute left-6 top-6 text-sm text-gray-400">
              {placeholder}
            </div>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
};

export default RichTextVisualEditor;