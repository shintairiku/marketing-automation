'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import NextImage from 'next/image';
import { AlertCircle, Bot, Copy, Download, Edit, Image, Loader2, Save, Sparkles, Trash2, Undo, Upload, Wand2, X } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { useArticleDetail } from '@/hooks/useArticles';
import { useAutoSave } from '@/hooks/useAutoSave';
import { cn } from '@/utils/cn';
import { useAuth } from '@clerk/nextjs';
import {
  closestCenter,
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import ArticlePreviewStyles from '../new-article/component/ArticlePreviewStyles';

import AIContentGenerationDialog from './components/AIContentGenerationDialog';
import BlockInsertButton from './components/BlockInsertButton';
import ContentSelectorDialog from './components/ContentSelectorDialog';
import HeadingLevelDialog from './components/HeadingLevelDialog';
import RichTextVisualEditor from './components/RichTextVisualEditor';
import SelectionManager from './components/SelectionManager';
import TableOfContentsDialog from './components/TableOfContentsDialog';

interface EditArticlePageProps {
  articleId: string;
}

interface ArticleBlock {
  id: string;
  type: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'p' | 'ul' | 'ol' | 'li' | 'img' | 'image_placeholder' | 'replaced_image' | 'div';
  content: string;
  isEditing: boolean;
  isSelected: boolean;
  // 画像プレースホルダー専用の追加フィールド
  placeholderData?: {
    placeholder_id: string;
    description_jp: string;
    prompt_en: string;
    alt_text?: string;
  };
  // 置き換えられた画像専用の追加フィールド
  imageData?: {
    image_id: string;
    image_url: string;
    alt_text: string;
  };
}

interface AiConfirmationState {
  blockId: string;
  originalType: ArticleBlock['type'];
  originalContent: string;
  newContent: string;
}


// Safe Image component that falls back to regular img on error
const SafeImage = ({ src, alt, className, style, width, height, onClick }: {
  src: string;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
  width?: number;
  height?: number;
  onClick?: (e: React.MouseEvent) => void;
}) => {
  const [imageError, setImageError] = useState(false);

  if (imageError) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={alt}
        className={className}
        style={{ objectFit: 'contain', ...style }}
        onClick={onClick}
        onError={() => console.warn('Image failed to load:', src)}
      />
    );
  }

  return (
    <NextImage
      src={src}
      alt={alt}
      width={width || 400}
      height={height || 300}
      className={className}
      style={{ objectFit: 'contain', ...style }}
      onClick={onClick}
      onError={() => setImageError(true)}
    />
  );
};

interface SortableBlockProps {
  id: string;
  disabled?: boolean;
  children: (props: SortableRenderProps) => React.ReactNode;
  onNodeChange?: (id: string, node: HTMLElement | null) => void;
}

interface SortableRenderProps {
  attributes: Record<string, any>;
  listeners: Record<string, any>;
  setActivatorNodeRef: (element: HTMLElement | null) => void;
  setNodeRef: (element: HTMLElement | null) => void;
  style: React.CSSProperties;
  isDragging: boolean;
  isOver: boolean;
}

const SortableBlock: React.FC<SortableBlockProps> = ({ id, disabled, children, onNodeChange }) => {
  const {
    attributes,
    listeners,
    setActivatorNodeRef,
    setNodeRef,
    transform,
    transition,
    isDragging,
    isOver,
  } = useSortable({ id, disabled });

  const composedNodeRef = useCallback(
    (node: HTMLElement | null) => {
      setNodeRef(node);
      if (onNodeChange) {
        onNodeChange(id, node);
      }
    },
    [id, onNodeChange, setNodeRef]
  );

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 90 : undefined,
  };

  return children({
    attributes,
    listeners: listeners ?? {},
    setActivatorNodeRef,
    setNodeRef: composedNodeRef,
    style,
    isDragging,
    isOver,
  });
};

const GripDots: React.FC = () => (
  <span className="grid grid-cols-2 gap-[2px] text-inherit">
    {Array.from({ length: 6 }).map((_, index) => (
      <span
        key={`dot-${index}`}
        className="h-[3px] w-[3px] rounded-full bg-current"
      />
    ))}
  </span>
);

const DropIndicator: React.FC = () => (
  <div className="pointer-events-none relative py-3">
    <div className="absolute inset-x-0 top-1/2 -translate-y-1/2">
      <div className="mx-auto flex max-w-4xl items-center gap-3 px-[3.25rem]">
        <span className="relative flex h-4 w-4 items-center justify-center">
          <span className="h-3 w-3 rounded-full border border-blue-500 bg-white shadow-sm" />
        </span>
        <span className="h-[3px] flex-1 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.35)]" />
      </div>
    </div>
  </div>
);

export default function EditArticlePage({ articleId }: EditArticlePageProps) {
  const { getToken } = useAuth();
  const { article, loading, error, refetch } = useArticleDetail(articleId);
  const [blocks, setBlocks] = useState<ArticleBlock[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  
  // 自動保存の制御状態
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true);

  const [hoveredBlockId, setHoveredBlockId] = useState<string | null>(null);
  const [aiEditingLoading, setAiEditingLoading] = useState(false);
  const [activeBlockSnapshot, setActiveBlockSnapshot] = useState<ArticleBlock | null>(null);
  const [dropIndicatorIndex, setDropIndicatorIndex] = useState<number | null>(null);
  const [draggingBlockIds, setDraggingBlockIds] = useState<string[]>([]);
  const blockRefs = useRef<Record<string, HTMLElement | null>>({});
  const draggingBlockIdsRef = useRef<string[]>([]);
  
  // 画像関連の状態
  const [imageUploadLoading, setImageUploadLoading] = useState<{ [blockId: string]: boolean }>({});
  const [imageGenerationLoading, setImageGenerationLoading] = useState<{ [blockId: string]: boolean }>({});
  const [imageApplyLoading, setImageApplyLoading] = useState<{ [blockId: string]: boolean }>({});
  const [historyLoading, setHistoryLoading] = useState<{ [blockId: string]: boolean }>({});
  
  const { toast } = useToast();
  const [imageHistoryVisible, setImageHistoryVisible] = useState<{ [blockId: string]: boolean }>({});
  const [imageHistory, setImageHistory] = useState<{ [placeholderId: string]: any[] }>({});
  
  // AI編集モーダル用state
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [aiInstruction, setAiInstruction] = useState("");
  const [lastAiInstruction, setLastAiInstruction] = useState(""); // 再生成用
  const [currentBlockForAi, setCurrentBlockForAi] = useState<ArticleBlock | null>(null);
  const [aiEditMode, setAiEditMode] = useState<'single' | 'bulk'>('single');

  const [aiConfirmations, setAiConfirmations] = useState<AiConfirmationState[]>([]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const blockIds = useMemo(() => blocks.map(block => block.id), [blocks]);

  useEffect(() => {
    const nextRefs: Record<string, HTMLElement | null> = {};
    blocks.forEach(block => {
      nextRefs[block.id] = blockRefs.current[block.id] ?? null;
    });
    blockRefs.current = nextRefs;
  }, [blocks]);

  // コンテンツ挿入関連のstate
  const [contentSelectorOpen, setContentSelectorOpen] = useState(false);
  const [tocDialogOpen, setTocDialogOpen] = useState(false);
  const [headingLevelDialogOpen, setHeadingLevelDialogOpen] = useState(false);
  const [aiContentDialogOpen, setAiContentDialogOpen] = useState(false);
  const [insertPosition, setInsertPosition] = useState<number>(0);
  const [editorView, setEditorView] = useState<'blocks' | 'visual'>('blocks');
  const [visualHtml, setVisualHtml] = useState('');
  const visualSyncTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const visualHtmlRef = useRef('');

  const selectedBlocksCount = useMemo(() => blocks.filter(b => b.isSelected).length, [blocks]);

  const updateDraggingGroup = useCallback((ids: string[]) => {
    draggingBlockIdsRef.current = ids;
    setDraggingBlockIds(ids);
  }, []);

  const updateSelection = useCallback((selectedIds: Set<string>) => {
    setBlocks(prev => {
      let changed = false;
      const next = prev.map(block => {
        const shouldSelect = selectedIds.has(block.id);
        if (block.isSelected !== shouldSelect) {
          changed = true;
          return { ...block, isSelected: shouldSelect };
        }
        return block;
      });
      return changed ? next : prev;
    });
  }, [setBlocks]);

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const activeId = String(event.active.id);
    const selectedIds = blocks.filter(block => block.isSelected).map(block => block.id);
    const isActiveSelected = selectedIds.includes(activeId);
    const groupIds = isActiveSelected && selectedIds.length > 1 ? selectedIds : [activeId];

    if (!isActiveSelected) {
      updateSelection(new Set([activeId]));
    }

    updateDraggingGroup(groupIds);

    const startBlock = blocks.find(block => block.id === activeId) || null;
    setActiveBlockSnapshot(startBlock);
    setDropIndicatorIndex(null);
  }, [blocks, updateDraggingGroup, updateSelection]);

  const handleDragOver = useCallback((event: DragOverEvent) => {
    const { active, over, delta } = event;
    if (!over) {
      setDropIndicatorIndex(null);
      return;
    }

    const activeId = String(active.id);
    const overId = String(over.id);
    const groupIds = draggingBlockIdsRef.current.length ? draggingBlockIdsRef.current : [activeId];
    const filteredBlocks = blocks.filter(block => !groupIds.includes(block.id));

    // Get the current mouse position via delta
    const activeRect = active.rect.current.translated ?? active.rect.current.initial;
    const overRect = over.rect;

    if (!activeRect || !overRect) {
      setDropIndicatorIndex(null);
      return;
    }

    // Calculate current position based on mouse cursor
    const currentMouseY = activeRect.top + (delta?.y ?? 0);
    const overBlockCenterY = overRect.top + overRect.height / 2;

    let targetIndex = filteredBlocks.findIndex(block => block.id === overId);

    if (targetIndex === -1) {
      // If hovering over a dragged block, find the nearest non-dragged block
      const overIndexInOriginal = blocks.findIndex(block => block.id === overId);
      if (overIndexInOriginal !== -1) {
        targetIndex = filteredBlocks.findIndex(block => {
          const indexInOriginal = blocks.findIndex(item => item.id === block.id);
          return indexInOriginal > overIndexInOriginal;
        });
        if (targetIndex === -1) {
          targetIndex = filteredBlocks.length;
        }
      } else {
        targetIndex = filteredBlocks.length;
      }
    }

    // Determine insertion point based on cursor position relative to block center
    const insertBelow = currentMouseY > overBlockCenterY;
    const insertionIndex = insertBelow ? targetIndex + 1 : targetIndex;
    const boundedIndex = Math.min(filteredBlocks.length, Math.max(0, insertionIndex));

    setDropIndicatorIndex(boundedIndex);
  }, [blocks]);

  const resetDragState = useCallback(() => {
    updateDraggingGroup([]);
    setActiveBlockSnapshot(null);
    setDropIndicatorIndex(null);
  }, [updateDraggingGroup]);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const targetIndex = dropIndicatorIndex;
    const groupIds = draggingBlockIdsRef.current.length ? draggingBlockIdsRef.current : [String(event.active.id)];

    if (targetIndex != null && groupIds.length > 0) {
      const groupSet = new Set(groupIds);
      setBlocks(prev => {
        const movingBlocks = prev.filter(block => groupSet.has(block.id));
        const remainingBlocks = prev.filter(block => !groupSet.has(block.id));
        const insertIndex = Math.min(targetIndex, remainingBlocks.length);
        const merged = [
          ...remainingBlocks.slice(0, insertIndex),
          ...movingBlocks,
          ...remainingBlocks.slice(insertIndex),
        ];
        return merged.map(block => (groupSet.has(block.id) ? { ...block, isSelected: true } : block));
      });
    }

    resetDragState();
  }, [dropIndicatorIndex, resetDragState, setBlocks]);

  const handleDragCancel = useCallback(() => {
    resetDragState();
  }, [resetDragState]);


  // Handle selection changes from SelectionManager
  const handleSelectionChange = useCallback((selectedIds: Set<string>) => {
    updateSelection(selectedIds);
  }, [updateSelection]);

  const handleBlockPointerDown = useCallback((blockId: string) => (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;

    const target = event.target as HTMLElement;
    const interactiveSelector = 'button, a[href], input, textarea, select, label, [role="button"], [contenteditable="true"]';

    if (target.closest(interactiveSelector)) return;
    if (target.closest('[data-interactive="true"]')) return;
    if (target.closest('[data-block-content="true"]')) return;
    if (target.closest('[data-selection-overlay="true"]')) return;
    if (target.closest('[data-selection-anchor="true"]')) return;

    event.preventDefault();

    const isModifier = event.shiftKey || event.metaKey || event.ctrlKey;

    setBlocks(prev => {
      const targetBlock = prev.find(item => item.id === blockId);
      const targetSelected = targetBlock?.isSelected ?? false;
      const selectedCount = prev.filter(item => item.isSelected).length;

      if (isModifier) {
        return prev.map(item =>
          item.id === blockId ? { ...item, isSelected: !targetSelected } : item
        );
      }

      if (targetSelected && selectedCount === 1) {
        return prev;
      }

      return prev.map(item => {
        if (item.id === blockId) {
          return { ...item, isSelected: true };
        }
        return item.isSelected ? { ...item, isSelected: false } : item;
      });
    });
  }, [setBlocks]);

  const indicatorReferenceBlocks = useMemo(() => {
    const draggingSet = new Set(draggingBlockIds);
    return blocks.filter(block => !draggingSet.has(block.id));
  }, [blocks, draggingBlockIds]);

  const dropIndicatorTargetId = dropIndicatorIndex != null && dropIndicatorIndex < indicatorReferenceBlocks.length
    ? indicatorReferenceBlocks[dropIndicatorIndex].id
    : null;

  const showDropIndicatorAtEnd = dropIndicatorIndex != null && dropIndicatorIndex >= indicatorReferenceBlocks.length && draggingBlockIds.length > 0;

  const draggingPreviewBlocks = useMemo(
    () =>
      draggingBlockIds
        .map(id => blocks.find(block => block.id === id))
        .filter((block): block is ArticleBlock => Boolean(block)),
    [draggingBlockIds, blocks]
  );

  const overlayBlocks = draggingPreviewBlocks.length > 0
    ? draggingPreviewBlocks
    : activeBlockSnapshot
      ? [activeBlockSnapshot]
      : [];

  // void要素の判定
  const isVoidElement = (tagName: string): boolean => {
    const voidElements = ['br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'];
    return voidElements.includes(tagName.toLowerCase());
  };

  const parseHtmlToBlocksInternal = useCallback((html: string): ArticleBlock[] => {
    const blocks: ArticleBlock[] = [];
    let blockIndex = 0;
    
    // DOMParserを使って正確にHTMLを解析
    const parser = new DOMParser();
    const doc = parser.parseFromString(`<div>${html}</div>`, 'text/html');
    const container = doc.body.firstElementChild;
    
    if (!container) return blocks;
    
    // 子要素を順番に処理
    Array.from(container.childNodes).forEach((node) => {
      if (node.nodeType === Node.COMMENT_NODE) {
        // コメントノード（画像プレースホルダー）の処理
        const commentContent = node.textContent?.trim() || '';
        const placeholderMatch = commentContent.match(/IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+)/);
        
        if (placeholderMatch) {
          const [, placeholderId, descriptionJp, promptEn] = placeholderMatch;
          
          blocks.push({
            id: `placeholder-${blockIndex++}`,
            type: 'image_placeholder',
            content: `<!-- ${commentContent} -->`,
            isEditing: false,
            isSelected: false,
            placeholderData: {
              placeholder_id: placeholderId.trim(),
              description_jp: descriptionJp.trim(),
              prompt_en: promptEn.trim(),
              alt_text: descriptionJp.trim(),
            },
          });
        }
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const element = node as Element;
        const tagName = element.tagName.toLowerCase();
        
        // 画像要素の特別処理
        if (tagName === 'img') {
          const placeholderIdAttr = element.getAttribute('data-placeholder-id');
          const imageIdAttr = element.getAttribute('data-image-id');
          const srcAttr = element.getAttribute('src');
          const altAttr = element.getAttribute('alt');
          
          if (placeholderIdAttr && imageIdAttr && srcAttr) {
            // 置き換えられた画像
            blocks.push({
              id: `image-${blockIndex++}`,
              type: 'replaced_image',
              content: element.outerHTML,
              isEditing: false,
              isSelected: false,
              placeholderData: {
                placeholder_id: placeholderIdAttr,
                description_jp: altAttr || '',
                prompt_en: '', // 復元時にAPIから取得
                alt_text: altAttr || '',
              },
              imageData: {
                image_id: imageIdAttr,
                image_url: srcAttr,
                alt_text: altAttr || '',
              },
            });
          } else {
            // 通常の画像
            blocks.push({
              id: `block-${blockIndex++}`,
              type: 'img',
              content: element.outerHTML,
              isEditing: false,
              isSelected: false,
            });
          }
        } else {
          // その他の要素
          const isEmpty = (tagName === 'ul' || tagName === 'ol') && 
                         !element.innerHTML.trim().replace(/<\/?li[^>]*>/g, '').trim();
          
          if (!isEmpty) {
            // 属性を保持するため、void要素以外でも一部の場合はouterHTMLを使用
            const hasImportantAttributes = element.hasAttribute('class') || 
                                         element.hasAttribute('id') || 
                                         element.hasAttribute('style') ||
                                         element.hasAttribute('href') ||
                                         element.hasAttribute('src') ||
                                         element.hasAttribute('target');
            
            blocks.push({
              id: `block-${blockIndex++}`,
              type: tagName as ArticleBlock['type'],
              content: (isVoidElement(tagName) || hasImportantAttributes) ? element.outerHTML : element.innerHTML,
              isEditing: false,
              isSelected: false,
            });
          }
        }
      } else if (node.nodeType === Node.TEXT_NODE) {
        // テキストノードの処理
        const textContent = node.textContent?.trim();
        if (textContent) {
          blocks.push({
            id: `block-${blockIndex++}`,
            type: 'p',
            content: textContent,
            isEditing: false,
            isSelected: false,
          });
        }
      }
    });
    
    return blocks.filter(block => {
      // 空のブロックや無効なブロックを除外
      if (!block.content || !block.content.trim()) return false;
      if (block.content === '<br>' || block.content === '<br />') return false;
      return true;
    });
  }, []);

  // HTMLコンテンツをブロックに分割（メモ化対応）
  const parseHtmlToBlocks = useMemo(() => {
    const cache = new Map<string, ArticleBlock[]>();
    return (html: string): ArticleBlock[] => {
      // 簡易ハッシュでキャッシュ
      const cacheKey = html.length + html.slice(0, 50) + html.slice(-50);
      if (cache.has(cacheKey)) {
        return cache.get(cacheKey)!;
      }

      const result = parseHtmlToBlocksInternal(html);
      cache.set(cacheKey, result);
      return result;
    };
  }, [parseHtmlToBlocksInternal]);

  // ブロックをHTMLに戻す（画像プレースホルダー対応）
  const blocksToHtml = useCallback((blocks: ArticleBlock[]): string => {
    return blocks.map(block => {
      if (block.type === 'image_placeholder') {
        // 画像プレースホルダーは完全な情報を含むコメント形式で出力
        if (block.placeholderData) {
          return `<!-- IMAGE_PLACEHOLDER: ${block.placeholderData.placeholder_id}|${block.placeholderData.description_jp}|${block.placeholderData.prompt_en} -->`;
        }
        return block.content;
      }
      
      if (block.type === 'replaced_image' && block.imageData) {
        // 置き換えられた画像は最新の画像データでimgタグを生成
        return `<img src="${block.imageData.image_url}" alt="${block.imageData.alt_text}" class="article-image" data-placeholder-id="${block.placeholderData?.placeholder_id}" data-image-id="${block.imageData.image_id}">`;
      }
      
      // void要素の特別な処理
      if (isVoidElement(block.type)) {
        // imgタグの場合、contentにすべての属性が含まれているはず
        if (block.type === 'img' && block.content) {
          return block.content;
        }
        // その他のvoid要素は自己完結タグとして出力
        return `<${block.type} />`;
      }
      
      // コンテンツが完全なHTMLタグの場合（outerHTMLから来た場合）はそのまま使用
      if (block.content.startsWith(`<${block.type}`)) {
        return block.content;
      }
      
      return `<${block.type}>${block.content}</${block.type}>`;
    }).join('\n');
  }, []);

  const handleEditorTabChange = useCallback((value: string) => {
    const nextView = value === 'visual' ? 'visual' : 'blocks';
    if (nextView === 'visual') {
      const html = blocksToHtml(blocks);
      visualHtmlRef.current = html;
      setVisualHtml(html);
    }
    setEditorView(nextView);
  }, [blocks, blocksToHtml]);

  const handleVisualEditorChange = useCallback((nextHtml: string) => {
    if (visualHtmlRef.current === nextHtml) {
      return;
    }

    visualHtmlRef.current = nextHtml;
    // Immediate state update for visual feedback
    setVisualHtml(nextHtml);

    if (visualSyncTimerRef.current) {
      clearTimeout(visualSyncTimerRef.current);
    }

    // Longer debounce to prevent excessive block parsing during typing
    visualSyncTimerRef.current = setTimeout(() => {
      setBlocks(parseHtmlToBlocks(nextHtml));
    }, 500);
  }, [parseHtmlToBlocks]);

  useEffect(() => {
    return () => {
      if (visualSyncTimerRef.current) {
        clearTimeout(visualSyncTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    visualHtmlRef.current = visualHtml;
  }, [visualHtml]);

  // 記事の画像を復元する関数
  const restoreArticleImages = useCallback(async () => {
    if (!article?.id) return;
    
    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      // 記事に関連する画像とプレースホルダー情報を取得
      const response = await fetch(`/api/proxy/images/article-images/${article.id}`, {
        method: 'GET',
        headers,
      });

      if (response.ok) {
        const imageData = await response.json();
        
        // 復元されたコンテンツがある場合は使用、なければ元のコンテンツを使用
        const contentToUse = imageData.restored_content || article.content;
        const parsedBlocks = parseHtmlToBlocks(contentToUse);
        
        // APIから取得したプレースホルダー情報でブロックデータを補完
        const enhancedBlocks = parsedBlocks.map(block => {
          if (block.type === 'image_placeholder' && block.placeholderData) {
            // APIデータからマッチするプレースホルダーを検索
            const matchingPlaceholder = imageData.placeholders?.find(
              (p: any) => p.placeholder_id === block.placeholderData?.placeholder_id
            );
            
            if (matchingPlaceholder) {
              return {
                ...block,
                placeholderData: {
                  ...block.placeholderData,
                  prompt_en: matchingPlaceholder.prompt_en || block.placeholderData.prompt_en,
                  description_jp: matchingPlaceholder.description_jp || block.placeholderData.description_jp,
                  alt_text: matchingPlaceholder.alt_text || block.placeholderData.alt_text,
                },
              };
            }
          }
          
          if (block.type === 'replaced_image' && block.placeholderData) {
            // 置き換えられた画像の場合も、プレースホルダー情報を補完
            const matchingPlaceholder = imageData.placeholders?.find(
              (p: any) => p.placeholder_id === block.placeholderData?.placeholder_id
            );
            
            if (matchingPlaceholder) {
              return {
                ...block,
                placeholderData: {
                  ...block.placeholderData,
                  prompt_en: matchingPlaceholder.prompt_en || block.placeholderData.prompt_en,
                  description_jp: matchingPlaceholder.description_jp || block.placeholderData.description_jp,
                  alt_text: matchingPlaceholder.alt_text || block.placeholderData.alt_text,
                },
              };
            }
          }
          
          return block;
        });
        
        setBlocks(enhancedBlocks);
        
        console.log('画像復元完了:', {
          placeholders: imageData.placeholders?.length || 0,
          images: imageData.all_images?.length || 0
        });
      } else {
        // APIエラーの場合は元のコンテンツを使用
        console.warn('画像復元APIエラー、元のコンテンツを使用します');
        setBlocks(parseHtmlToBlocks(article.content));
      }
    } catch (error) {
      console.error('画像復元エラー:', error);
      // エラーの場合は元のコンテンツを使用
      setBlocks(parseHtmlToBlocks(article.content));
    }
  }, [article?.id, article?.content, getToken, parseHtmlToBlocks]);

  // 記事データが更新されたときにブロックを再構築（画像復元含む）
  useEffect(() => {
    if (article?.content) {
      restoreArticleImages();
    }
  }, [article, restoreArticleImages]);

  const handleSelectionToggle = (blockId: string, checked: boolean | 'indeterminate') => {
    setBlocks(prev => 
      prev.map(block => 
        block.id === blockId ? { ...block, isSelected: !!checked } : block
      )
    );
  };

  // コンテンツ挿入の処理
  const handleInsertContent = (type: string, position: number) => {
    setInsertPosition(position);
    if (type === 'selector') {
      setContentSelectorOpen(true);
    }
  };

  // 新しいブロックを作成するヘルパー関数
  const createNewBlock = (type: ArticleBlock['type'], content: string = ''): ArticleBlock => {
    return {
      id: `block-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      content,
      isEditing: false,
      isSelected: false
    };
  };

  // コンテンツタイプ選択の処理
  const handleSelectContentType = (type: string) => {
    if (type === 'table-of-contents') {
      setTocDialogOpen(true);
    } else if (type === 'heading') {
      setHeadingLevelDialogOpen(true);
    } else {
      // テキストブロックの追加
      let blockType: ArticleBlock['type'] = 'p';
      let initialContent = '';

      switch (type) {
        case 'paragraph':
          blockType = 'p';
          initialContent = 'ここにテキストを入力してください...';
          break;
        case 'unordered-list':
          blockType = 'ul';
          initialContent = '<li>リストアイテム 1</li><li>リストアイテム 2</li>';
          break;
        case 'ordered-list':
          blockType = 'ol';
          initialContent = '<li>番号付きアイテム 1</li><li>番号付きアイテム 2</li>';
          break;
        default:
          blockType = 'p';
          initialContent = '新しいブロック';
      }

      const newBlock = createNewBlock(blockType, initialContent);
      insertNewBlock(newBlock);
    }

    // ダイアログを閉じる
    setContentSelectorOpen(false);
  };

  // 見出しレベル選択の処理
  const handleSelectHeadingLevel = (level: number) => {
    const blockType = `h${level}` as ArticleBlock['type'];
    const initialContent = `見出し ${level}`;
    const newBlock = createNewBlock(blockType, initialContent);
    insertNewBlock(newBlock);
  };

  // AIコンテンツ生成の開始
  const handleAIGenerate = (position: number) => {
    setInsertPosition(position);
    setAiContentDialogOpen(true);
  };

  // AIコンテンツ生成の完了
  const handleAIContentGenerated = (blocks: Array<{
    type: 'heading' | 'paragraph';
    content: string;
    level?: number;
  }>) => {
    // 生成されたブロックをArticleBlockに変換して挿入
    blocks.forEach((block, index) => {
      let articleBlock: ArticleBlock;

      if (block.type === 'heading') {
        const level = block.level || 2;
        articleBlock = createNewBlock(`h${level}` as ArticleBlock['type'], block.content);
      } else {
        articleBlock = createNewBlock('p', block.content);
      }

      // 複数ブロックの場合は順番に挿入
      setBlocks(prev => {
        const newBlocks = [...prev];
        const safeInsertPos = Math.min(insertPosition + index, newBlocks.length);
        newBlocks.splice(safeInsertPos, 0, articleBlock);
        return newBlocks;
      });
    });

    setAiContentDialogOpen(false);
  };

  // ブロック挿入の共通処理
  const insertNewBlock = (newBlock: ArticleBlock) => {
    // 指定された位置にブロックを挿入
    setBlocks(prev => {
      const newBlocks = [...prev];
      const safeInsertPos = Math.min(insertPosition, newBlocks.length);
      newBlocks.splice(safeInsertPos, 0, newBlock);
      return newBlocks;
    });

    // 挿入後、新しいブロックを編集モードにする
    setTimeout(() => {
      startEditing(newBlock.id);
    }, 100);
  };

  // 目次の挿入と見出しIDの更新
  const handleInsertToc = (tocHtml: string, updatedHtmlContent: string) => {
    console.log('handleInsertToc called with tocHtml:', tocHtml);
    
    // シンプルな連番IDを生成する関数（TableOfContentsDialogと同じロジック）
    const generateSafeId = (text: string, index: number): string => {
      return `heading-${index + 1}`;
    };

    // 目次ブロックを作成
    const newBlock: ArticleBlock = {
      id: `toc-${Date.now()}`,
      type: 'div' as any,
      content: tocHtml,
      isEditing: false,
      isSelected: false
    };

    // テキスト全体にID割り当て済みのHTMLを基にブロックを再構築
    // これにより、入れ子の見出しも含めて確実にIDが同期される
    let rebuiltBlocks = parseHtmlToBlocks(updatedHtmlContent || blocksToHtml(blocks));

    // 既存の目次（旧実装や他のTOC）らしきブロックを除去
    // 目次は通常 <div> 内に <nav> を含むため、それをヒューリスティックに検出
    rebuiltBlocks = rebuiltBlocks.filter(b => {
      if (b.type !== 'div') return true;
      const html = (b.content || '').toLowerCase();
      // data-toc マーカー、または <nav> を含む div は TOC とみなして除外
      if (html.includes('data-toc="true"')) return false;
      if (html.includes('<nav')) return false;
      return true;
    });

    // 目次を指定位置に挿入
    const safeInsertPos = Math.min(insertPosition, rebuiltBlocks.length);
    rebuiltBlocks.splice(safeInsertPos, 0, newBlock);
    
    console.log('Final blocks after TOC insertion (rebuilt):', rebuiltBlocks);
    setBlocks(rebuiltBlocks);
    setTocDialogOpen(false);
  };
  
  // ブロック編集の開始
  const startEditing = (blockId: string) => {
    setBlocks(prev => prev.map(block => 
      block.id === blockId ? { ...block, isEditing: true, isSelected: false } : { ...block, isEditing: false }
    ));
  };

  // ブロック編集の保存
  const saveBlock = (blockId: string, newContent: string) => {
    setBlocks(prev => prev.map(block => 
      block.id === blockId ? { ...block, content: newContent, isEditing: false } : block
    ));
  };

  // ブロック編集のキャンセル
  const cancelEditing = (blockId: string) => {
    setBlocks(prev => prev.map(block => 
      block.id === blockId ? { ...block, isEditing: false } : block
    ));
  };

  // ブロック削除 (単一)
  const deleteBlock = (blockId: string) => {
    setBlocks(prev => prev.filter(b => b.id !== blockId));
  };

  // 一括削除
  const handleBulkDelete = () => {
    if (window.confirm(`${selectedBlocksCount}件のブロックを本当に削除しますか？`)) {
      setBlocks(prev => prev.filter(b => !b.isSelected));
    }
  };

  // AI編集モーダルを開く
  const openAiModal = (mode: 'single' | 'bulk', block?: ArticleBlock) => {
    setAiEditMode(mode);
    if (mode === 'single' && block) {
      setCurrentBlockForAi(block);
    } else {
      setCurrentBlockForAi(null);
    }
    setIsAiModalOpen(true);
  };
  
  // AI 編集実行
  const runAiEdit = async () => {
    try {
      setAiEditingLoading(true);
      setAiConfirmations([]);
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      if (aiEditMode === 'bulk') {
        const targets = blocks.filter(b => b.isSelected && !isVoidElement(b.type));
        const editPromises = targets.map(block => 
          fetch(`/api/proxy/articles/${articleId}/ai-edit`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              content: `<${block.type}>${block.content}</${block.type}>`,
              instruction: aiInstruction
            })
          }).then(res => res.json())
        );
        const results = await Promise.all(editPromises);
        
        const newConfirmations = results.map((result, index) => {
          const targetBlock = targets[index];
          return {
            blockId: targetBlock.id,
            originalType: targetBlock.type,
            originalContent: targetBlock.content,
            newContent: result.edited_content || `AIによる編集に失敗しました: ${result.detail || '不明なエラー'}`
          };
        });
        setAiConfirmations(newConfirmations);
        
      } else if (currentBlockForAi) {
        const requestContent = `<${currentBlockForAi.type}>${currentBlockForAi.content}</${currentBlockForAi.type}>`;
        console.log('AI編集リクエスト:', {
          content: requestContent,
          instruction: aiInstruction,
          url: `/api/proxy/articles/${articleId}/ai-edit`
        });
        
        const resp = await fetch(`/api/proxy/articles/${articleId}/ai-edit`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            content: requestContent,
            instruction: aiInstruction
          })
        });

        console.log('AI編集レスポンス:', {
          status: resp.status,
          statusText: resp.statusText,
          ok: resp.ok
        });

        if (!resp.ok) {
          const errorData = await resp.json().catch(() => ({ detail: 'レスポンスがJSON形式ではありません' }));
          console.error('AI編集エラーレスポンス:', errorData);
          throw new Error(`AI編集に失敗しました: ${errorData.detail || resp.statusText}`);
        }
        
        const result = await resp.json();
        console.log('AI編集結果:', result);

        if (!result.edited_content) {
          console.error('AI編集結果が空です:', result);
          throw new Error('AIによる編集結果が空でした。もう一度お試しください。');
        }

        const aiConfirmationState: AiConfirmationState = {
          blockId: currentBlockForAi.id,
          originalType: currentBlockForAi.type,
          originalContent: currentBlockForAi.content,
          newContent: result.edited_content
        };
        setAiConfirmations([aiConfirmationState]);
      }
      
      // 再生成用に最後の指示を保存
      setLastAiInstruction(aiInstruction);
    } catch (error) {
      console.error('AI編集エラー:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      alert(`AI編集に失敗しました。 ${errorMessage}`);
    } finally {
      setAiEditingLoading(false);
      setIsAiModalOpen(false);
      setAiInstruction("");
    }
  };

  const handleRegenerate = async (blockId: string) => {
    const confirmation = aiConfirmations.find(c => c.blockId === blockId);
    if (!confirmation || !lastAiInstruction) {
      console.warn('再生成に必要な情報が不足:', { confirmation, lastAiInstruction });
      return;
    }

    try {
      setAiEditingLoading(true);
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const requestContent = `<${confirmation.originalType}>${confirmation.originalContent}</${confirmation.originalType}>`;
      console.log('AI再編集リクエスト:', {
        content: requestContent,
        instruction: lastAiInstruction,
        blockId
      });

      const resp = await fetch(`/api/proxy/articles/${articleId}/ai-edit`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          content: requestContent,
          instruction: lastAiInstruction
        })
      });

      console.log('AI再編集レスポンス:', {
        status: resp.status,
        statusText: resp.statusText,
        ok: resp.ok
      });

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({ detail: 'レスポンスがJSON形式ではありません' }));
        console.error('AI再編集エラーレスポンス:', errorData);
        throw new Error(`AI再編集に失敗しました: ${errorData.detail || resp.statusText}`);
      }

      const result = await resp.json();
      console.log('AI再編集結果:', result);

      if (!result.edited_content) {
        console.error('AI再編集結果が空です:', result);
        throw new Error('AIによる再編集結果が空でした。もう一度お試しください。');
      }
      
      setAiConfirmations(prev => prev.map(c => 
        c.blockId === blockId ? { ...c, newContent: result.edited_content } : c
      ));

    } catch (error) {
      console.error('AI再編集エラー:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      alert(`AI再編集に失敗しました。 ${errorMessage}`);
    } finally {
      setAiEditingLoading(false);
    }
  };

  const handleApprove = (blockId: string) => {
    const confirmation = aiConfirmations.find(c => c.blockId === blockId);
    if (confirmation) {
      setBlocks(prev => prev.map(b => 
        b.id === blockId ? { ...b, content: confirmation.newContent } : b
      ));
      setAiConfirmations(prev => prev.filter(c => c.blockId !== blockId));
    }
  };

  const handleCancel = (blockId: string) => {
    setAiConfirmations(prev => prev.filter(c => c.blockId !== blockId));
  };
  
  const handleApproveAll = () => {
    setBlocks(prev => {
      const updatedBlocks = [...prev];
      aiConfirmations.forEach(confirmation => {
        const blockIndex = updatedBlocks.findIndex(b => b.id === confirmation.blockId);
        if (blockIndex !== -1) {
          updatedBlocks[blockIndex] = {
            ...updatedBlocks[blockIndex],
            content: confirmation.newContent,
          };
        }
      });
      return updatedBlocks;
    });
    setAiConfirmations([]);
  };

  const handleCancelAll = () => {
    setAiConfirmations([]);
  };

  const handleImageUpload = async (blockId: string, file: File) => {
    const block = blocks.find(b => b.id === blockId);
    if (!block || !block.placeholderData) return;

    try {
      setImageUploadLoading(prev => ({ ...prev, [blockId]: true }));
      const formData = new FormData();
      formData.append('file', file);
      formData.append('article_id', articleId);
      formData.append('placeholder_id', block.placeholderData.placeholder_id);
      formData.append('alt_text', block.placeholderData.alt_text || block.placeholderData.description_jp);

      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`/api/proxy/images/upload`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to parse error response' }));
        throw new Error(`Upload failed: ${errorData.detail || response.statusText}`);
      }

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.message || 'Upload failed for an unknown reason');
      }
      
      // ブロックを置き換えられた画像タイプに更新
      setBlocks(prev => prev.map(b => 
        b.id === blockId 
          ? { 
              ...b, 
              type: 'replaced_image', 
              content: '', // コンテンツはimageDataからレンダリングされる
              imageData: {
                image_id: result.image_id,
                image_url: result.image_url,
                alt_text: block.placeholderData?.alt_text || block.placeholderData?.description_jp || '',
              }
            }
          : b
      ));
      
      alert('画像が正常にアップロードされました！');

    } catch (error) {
      console.error('画像アップロードエラー:', error);
      alert('画像のアップロードに失敗しました。');
    } finally {
      setImageUploadLoading(prev => ({ ...prev, [blockId]: false }));
    }
  };

  // 画像生成処理（新しいAPIを使用）
  const handleImageGeneration = async (blockId: string) => {
    const block = blocks.find(b => b.id === blockId);
    if (!block || !block.placeholderData) return;

    const placeholderData = block.placeholderData;

    try {
      setImageGenerationLoading(prev => ({ ...prev, [blockId]: true }));

      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      // 新しいAPIを使用：画像生成してプレースホルダーと関連付け（記事更新はしない）
      const response = await fetch(`/api/proxy/images/generate-and-link`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          placeholder_id: placeholderData.placeholder_id,
          description_jp: placeholderData.description_jp,
          prompt_en: placeholderData.prompt_en,
          alt_text: placeholderData.alt_text || placeholderData.description_jp,
          article_id: articleId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Generation failed: ${response.status}`);
      }

      const result = await response.json();
      
      // 画像生成成功後、記事HTMLに反映するためreplace-placeholderを呼び出し
      const replaceResponse = await fetch(`/api/proxy/images/replace-placeholder`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          article_id: articleId,
          placeholder_id: placeholderData.placeholder_id,
          image_url: result.image_url,
          alt_text: result.alt_text,
        }),
      });

      if (!replaceResponse.ok) {
        throw new Error(`Replace failed: ${replaceResponse.status}`);
      }

      const replaceResult = await replaceResponse.json();
      
      // ブロックを置き換えられた画像タイプに更新（replace-placeholderの結果を使用）
      setBlocks(prev => prev.map(b => 
        b.id === blockId 
          ? { 
              ...b, 
              type: 'replaced_image', 
              content: replaceResult.updated_content.match(new RegExp(`<img[^>]*data-placeholder-id="${placeholderData.placeholder_id}"[^>]*>`))?.[0] || 
                       `<img src="${result.image_url}" alt="${result.alt_text}" class="article-image" data-placeholder-id="${placeholderData.placeholder_id}" data-image-id="${replaceResult.image_id || result.image_id}" />`,
              imageData: {
                image_id: replaceResult.image_id || result.image_id,
                image_url: result.image_url,
                alt_text: result.alt_text,
              }
            }
          : b
      ));

      toast({
        title: "画像生成完了",
        description: "画像が生成され記事に適用されました。",
        variant: "default",
      });
    } catch (error) {
      console.error('画像生成エラー:', error);
      toast({
        title: "画像生成に失敗",
        description: "画像の生成に失敗しました。再試行してください。",
        variant: "destructive",
      });
    } finally {
      setImageGenerationLoading(prev => ({ ...prev, [blockId]: false }));
    }
  };

  // 画像をプレースホルダーに復元
  const handleImageRestore = async (blockId: string) => {
    const block = blocks.find(b => b.id === blockId);
    if (!block || !block.placeholderData) return;

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`/api/proxy/images/restore-placeholder`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          article_id: articleId,
          placeholder_id: block.placeholderData.placeholder_id,
        }),
      });

      if (!response.ok) {
        throw new Error(`Restore failed: ${response.status}`);
      }

      const result = await response.json();
      
      // ブロックをプレースホルダータイプに戻す（サーバ返却の placeholder で placeholderData を更新）
      setBlocks(prev => prev.map(b => 
        b.id === blockId 
          ? { 
              ...b, 
              type: 'image_placeholder', 
              content: result.placeholder_comment || 
                       result.updated_content.match(new RegExp(`<!-- IMAGE_PLACEHOLDER: ${b.placeholderData?.placeholder_id}\\|[^>]+ -->`))?.[0] || 
                       b.content,
              placeholderData: b.placeholderData ? {
                ...b.placeholderData,
                // サーバ返却値で必ず上書き（空値のままにしない）
                placeholder_id: result.placeholder?.placeholder_id ?? b.placeholderData.placeholder_id,
                description_jp: result.placeholder?.description_jp ?? b.placeholderData.description_jp,
                prompt_en:      result.placeholder?.prompt_en ?? b.placeholderData.prompt_en,
                alt_text:       result.placeholder?.alt_text ?? b.placeholderData.alt_text,
              } : b.placeholderData,
              imageData: undefined
            }
          : b
      ));

      toast({
        title: "プレースホルダーに戻しました",
        description: "画像がプレースホルダーに戻されました。",
        variant: "default",
      });
    } catch (error) {
      console.error('画像復元エラー:', error);
      toast({
        title: "復元に失敗",
        description: "画像の復元に失敗しました。再試行してください。",
        variant: "destructive",
      });
    }
  };

  // 画像履歴を取得
  const fetchImageHistory = async (placeholderId: string, blockId?: string) => {
    if (blockId) {
      setHistoryLoading(prev => ({ ...prev, [blockId]: true }));
    }
    
    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`/api/proxy/images/placeholder-history/${articleId}/${placeholderId}`, {
        method: 'GET',
        headers,
      });

      if (response.ok) {
        const data = await response.json();
        setImageHistory(prev => ({
          ...prev,
          [placeholderId]: data.images_history || []
        }));
        return data.images_history || [];
      } else {
        toast({
          title: "履歴取得に失敗",
          description: "画像履歴の取得に失敗しました。再試行してください。",
          variant: "destructive",
        });
        return [];
      }
    } catch (error) {
      console.error('画像履歴取得エラー:', error);
      toast({
        title: "履歴取得エラー",
        description: "ネットワークエラーが発生しました。",
        variant: "destructive",
      });
      return [];
    } finally {
      if (blockId) {
        setHistoryLoading(prev => ({ ...prev, [blockId]: false }));
      }
    }
  };

  // 過去の画像を選択してプレースホルダーに適用
  const applyHistoryImage = async (blockId: string, imageData: any) => {
    const block = blocks.find(b => b.id === blockId);
    if (!block || !block.placeholderData) return;

    setImageApplyLoading(prev => ({ ...prev, [blockId]: true }));

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      // 画像をプレースホルダーで置き換え
      const response = await fetch(`/api/proxy/images/replace-placeholder`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          article_id: articleId,
          placeholder_id: block.placeholderData.placeholder_id,
          image_url: imageData.gcs_url || imageData.file_path,
          alt_text: imageData.alt_text || block.placeholderData.description_jp,
        }),
      });

      if (!response.ok) {
        throw new Error(`Replace failed: ${response.status}`);
      }

      const result = await response.json();
      
      // ブロックを置き換えられた画像タイプに更新
      const extractedContent = result.updated_content.match(new RegExp(`<img[^>]*data-placeholder-id="${block.placeholderData!.placeholder_id}"[^>]*>`))?.[0];
      
      if (!extractedContent) {
        // もしextractに失敗した場合は記事全体を再取得
        await refetch();
      } else {
        setBlocks(prev => prev.map(b => 
          b.id === blockId 
            ? { 
                ...b, 
                type: 'replaced_image', 
                content: extractedContent,
                imageData: {
                  image_id: result.image_id,
                  image_url: imageData.gcs_url || imageData.file_path,
                  alt_text: imageData.alt_text || block.placeholderData!.description_jp,
                }
              }
            : b
        ));
      }

      // 画像履歴を非表示にする
      setImageHistoryVisible(prev => ({ ...prev, [blockId]: false }));
      
      toast({
        title: "画像適用完了",
        description: "過去の画像が適用されました。",
        variant: "default",
      });
    } catch (error) {
      console.error('画像適用エラー:', error);
      toast({
        title: "画像適用に失敗",
        description: "画像の適用に失敗しました。再試行してください。",
        variant: "destructive",
      });
    } finally {
      setImageApplyLoading(prev => ({ ...prev, [blockId]: false }));
    }
  };

  // 画像履歴の表示切り替え
  const toggleImageHistory = async (blockId: string, placeholderId: string) => {
    const isVisible = imageHistoryVisible[blockId];
    
    if (!isVisible) {
      // 履歴を表示する場合は、データを取得
      await fetchImageHistory(placeholderId, blockId);
    }
    
    setImageHistoryVisible(prev => ({
      ...prev,
      [blockId]: !isVisible
    }));
  };

  // ファイル選択のトリガー
  const triggerFileUpload = (blockId: string) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleImageUpload(blockId, file);
      }
    };
    input.click();
  };

  // HTMLエクスポート機能
  const exportAsHtml = () => {
    const htmlContent = blocksToHtml(blocks);
    return htmlContent;
  };

  // HTMLをクリップボードにコピー
  const copyHtmlToClipboard = async () => {
    try {
      const htmlContent = exportAsHtml();
      await navigator.clipboard.writeText(htmlContent);
      alert('HTMLがクリップボードにコピーされました！');
    } catch (error) {
      console.error('コピーに失敗しました:', error);
      alert('コピーに失敗しました。');
    }
  };

  // HTMLファイルとしてダウンロード
  const downloadHtmlFile = () => {
    try {
      const htmlContent = exportAsHtml();
      const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${article?.title || 'article'}.html`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      alert('HTMLファイルがダウンロードされました！');
    } catch (error) {
      console.error('ダウンロードに失敗しました:', error);
      alert('ダウンロードに失敗しました。');
    }
  };

  // 記事全体の保存
  const saveArticle = async () => {
    if (!article) return;

    try {
      setIsSaving(true);
      setSaveError(null);

      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const updatedContent = blocksToHtml(blocks);
      
      // 空のimgタグを含むコンテンツの保存を防ぐ
      if (updatedContent.includes('<img />') || updatedContent.includes('<img/>')) {
        console.warn('Preventing save of content with empty img tags');
        alert('空の画像タグが含まれているため、保存できません。画像を正しく設定してください。');
        return;
      }

      const response = await fetch(`/api/proxy/articles/${articleId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({
          content: updatedContent,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "レスポンスがJSON形式ではありません" }));
        throw new Error(`Save failed: ${errorData.detail || response.statusText}`);
      }
      
      await refetch();
      alert('記事が正常に保存されました！');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('記事の保存に失敗しました:', errorMessage);
      setSaveError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  // 自動保存用のラッパー関数
  const autoSaveArticle = useCallback(async () => {
    if (!article || isSaving) return;

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const updatedContent = blocksToHtml(blocks);
      
      // 空のimgタグを含むコンテンツの保存を防ぐ
      if (updatedContent.includes('<img />') || updatedContent.includes('<img/>')) {
        console.warn('自動保存をスキップ: 空の画像タグが含まれています');
        return;
      }

      const response = await fetch(`/api/proxy/articles/${articleId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({
          content: updatedContent,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "レスポンスがJSON形式ではありません" }));
        throw new Error(`自動保存失敗: ${errorData.detail || response.statusText}`);
      }
      
      console.log('自動保存が完了しました');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('自動保存エラー:', errorMessage);
      throw error; // useAutoSaveフックがエラーを処理します
    }
  }, [article, articleId, blocks, blocksToHtml, getToken, isSaving]);


  // Content extractor for efficient comparison
  const contentExtractor = useCallback((blocks: ArticleBlock[]) => {
    return blocks.map(b => b.content).join('');
  }, []);

  // 自動保存フックの設定
  const autoSave = useAutoSave(blocks, autoSaveArticle, {
    delay: 3000, // 3秒のデバウンスで応答性を向上
    enabled: autoSaveEnabled && !!article && blocks.length > 0,
    contentExtractor, // HTMLコンテンツのみを比較対象に
    maxRetries: 3, // 最大3回リトライ
    retryDelay: 1000, // 1秒後にリトライ開始
    excludeKeys: ['isEditing', 'isSelected'], // UI状態を除外
  });

  // 自動保存の制御: 特定の操作中は無効化
  useEffect(() => {
    // AI編集中、手動保存中、画像関連の操作中は自動保存を無効化
    const hasAnyLoading = aiEditingLoading || 
                         isSaving || 
                         Object.values(imageUploadLoading).some(loading => loading) ||
                         Object.values(imageGenerationLoading).some(loading => loading) ||
                         Object.values(imageApplyLoading).some(loading => loading) ||
                         Object.values(historyLoading).some(loading => loading);
    
    if (hasAnyLoading) {
      setAutoSaveEnabled(false);
    } else {
      // 操作が完了したら少し遅延してから自動保存を再有効化
      const timer = setTimeout(() => {
        setAutoSaveEnabled(true);
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [aiEditingLoading, isSaving, imageUploadLoading, imageGenerationLoading, historyLoading, imageApplyLoading]);

  // 初期化時は自動保存を無効化（画像復元完了まで）
  useEffect(() => {
    if (loading) {
      setAutoSaveEnabled(false);
    } else if (article && blocks.length > 0) {
      // 記事とブロックが読み込まれたら自動保存を有効化
      const timer = setTimeout(() => {
        setAutoSaveEnabled(true);
      }, 2000); // 画像復元などの初期化完了を待つ
      
      return () => clearTimeout(timer);
    }
  }, [loading, article, blocks.length]);


  // ブロックコンテンツのレンダリング（リッチプレビュー対応）
  const renderBlockContent = (block: ArticleBlock) => {
    const tagName = block.type;
    
    // 置き換えられた画像の場合は専用レンダリング
    if (block.type === 'replaced_image' && block.imageData) {
      return (
        <div key={block.id}>
          <SafeImage 
            src={block.imageData.image_url} 
            alt={block.imageData.alt_text} 
            className="article-image"
            style={{ maxHeight: '400px' }}
            width={800}
            height={400}
          />
        </div>
      );
    }
    
    // void要素の場合は特別処理
    if (isVoidElement(tagName)) {
      return React.createElement(tagName, { 
        key: block.id
      });
    }
    
    // 通常の要素
    // コンテンツが完全なHTMLタグの場合は、直接レンダリング
    if (block.content.startsWith(`<${tagName}`)) {
      return (
        <div 
          key={block.id}
          dangerouslySetInnerHTML={{ __html: block.content }}
        />
      );
    }
    
    return React.createElement(tagName, {
      dangerouslySetInnerHTML: { __html: block.content },
      key: block.id
    });
  };

  const stripHtml = (html: string) => html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

  const renderDragOverlayBlock = (block: ArticleBlock) => {
    if (block.type === 'replaced_image' && block.imageData) {
      return (
        <div className="flex flex-col items-center gap-2">
          <SafeImage
            src={block.imageData.image_url}
            alt={block.imageData.alt_text}
            className="max-h-40 w-full rounded-lg object-cover"
            width={600}
            height={240}
          />
          <span className="text-xs text-gray-500">{block.imageData.alt_text}</span>
        </div>
      );
    }

    if (block.type === 'image_placeholder' && block.placeholderData) {
      return (
        <div className="rounded-md border border-dashed border-purple-300 bg-purple-50 px-4 py-3 text-sm text-purple-700">
          <div className="font-medium">画像プレースホルダー</div>
          <div className="text-xs opacity-80">ID: {block.placeholderData.placeholder_id}</div>
          <div className="mt-1 text-xs leading-relaxed">{block.placeholderData.description_jp}</div>
        </div>
      );
    }

    const previewText = stripHtml(block.content || '') || '(空のコンテンツ)';

    if (['ul', 'ol'].includes(block.type)) {
      return (
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">
          {previewText.split(/\s*[•\-\d.]+\s*/).filter(Boolean).slice(0, 4).map((item, index) => (
            <li key={`${block.id}-preview-${index}`}>{item}</li>
          ))}
        </ul>
      );
    }

    return <p className="text-sm leading-relaxed text-gray-700">{previewText}</p>;
  };

  // 画像プレースホルダーブロックのレンダリング
  const renderImagePlaceholderBlock = (block: ArticleBlock) => {
    if (!block.placeholderData) return null;

    const placeholderId = block.placeholderData.placeholder_id;
    const historyImages = imageHistory[placeholderId] || [];
    const isHistoryVisible = imageHistoryVisible[block.id];

    return (
      <div className="border-2 border-dashed border-blue-300 bg-blue-50 rounded-lg p-6 mb-4 not-prose">
        <div className="flex items-center gap-3 mb-3">
          <Image className="h-6 w-6 text-blue-600" aria-label="画像プレースホルダーアイコン" />
          <div className="flex-1">
            <h4 className="font-medium text-blue-900">画像プレースホルダー</h4>
            <p className="text-sm text-blue-700">ID: {block.placeholderData.placeholder_id}</p>
          </div>
          <div className="flex gap-2">
            <Button 
              size="sm" 
              variant="outline" 
              className="text-purple-600 border-purple-300 hover:bg-purple-100"
              onClick={() => toggleImageHistory(block.id, placeholderId)}
              disabled={historyLoading[block.id]}
            >
              {historyLoading[block.id] ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  読込中
                </>
              ) : isHistoryVisible ? '履歴を隠す' : `履歴 (${historyImages.length})`}
            </Button>
            <Button 
              size="sm" 
              variant="outline" 
              className="text-blue-600 border-blue-300 hover:bg-blue-100"
              onClick={() => triggerFileUpload(block.id)}
              disabled={imageUploadLoading[block.id]}
            >
              {imageUploadLoading[block.id] ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-1" />
              ) : (
                <Upload className="h-4 w-4 mr-1" />
              )}
              アップロード
            </Button>
            <Button 
              size="sm" 
              className="bg-blue-600 hover:bg-blue-700 text-white"
              onClick={() => handleImageGeneration(block.id)}
              disabled={imageGenerationLoading[block.id]}
            >
              {imageGenerationLoading[block.id] ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-1" />
              ) : (
                <Sparkles className="h-4 w-4 mr-1" />
              )}
              AI生成
            </Button>
          </div>
        </div>
        
        {/* 画像履歴表示 */}
        {isHistoryVisible && (
          <div 
            className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg"
            data-history-panel
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
          >
            <h5 className="font-medium text-purple-900 mb-2">生成済み画像履歴</h5>
            {historyImages.length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {historyImages.map((image, index) => (
                  <button
                    key={image.id}
                    type="button"
                    className="relative group block focus:outline-none rounded-lg"
                    data-history-tile
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!imageApplyLoading[block.id]) applyHistoryImage(block.id, image);
                    }}
                    onMouseDown={(e) => e.stopPropagation()}
                    onPointerDown={(e) => e.stopPropagation()}
                    disabled={!!imageApplyLoading[block.id]}
                    aria-label="この履歴画像を適用"
                  >
                    <SafeImage 
                      src={image.gcs_url || image.file_path} 
                      alt={image.alt_text || `生成画像 ${index + 1}`}
                      className={`w-full h-24 object-cover rounded-lg ${
                        imageApplyLoading[block.id] ? 'opacity-50' : 'cursor-pointer'
                      }`}
                      width={100}
                      height={96}
                    />
                    <div className="absolute bottom-1 right-1 bg-black bg-opacity-60 text-white text-xs px-1 py-0.5 rounded">
                      {new Date(image.created_at).toLocaleDateString()}
                    </div>
                    <div className={`absolute inset-0 bg-blue-500 transition-all duration-200 rounded-lg flex items-center justify-center pointer-events-none ${
                      imageApplyLoading[block.id] 
                        ? 'bg-opacity-70' 
                        : 'bg-opacity-0 hover:bg-opacity-20'
                    }`}>
                      {imageApplyLoading[block.id] ? (
                        <div className="text-white font-medium flex flex-col items-center">
                          <Loader2 className="w-6 h-6 animate-spin mb-1" />
                          <span className="text-xs">適用中</span>
                        </div>
                      ) : (
                        <span className="text-white font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                          選択
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            ) : historyLoading[block.id] ? (
              <div className="text-purple-600 text-sm text-center py-4">
                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                履歴を読み込み中...
              </div>
            ) : (
              <div className="text-purple-600 text-sm text-center py-4">
                <p className="mb-2">まだ画像が生成されていません</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => fetchImageHistory(placeholderId, block.id)}
                  className="text-purple-600 border-purple-300 hover:bg-purple-100"
                >
                  再読み込み
                </Button>
              </div>
            )}
          </div>
        )}

        <div className="space-y-2 text-sm">
          <div>
            <span className="font-medium text-gray-700">説明: </span>
            <span className="text-gray-600">{block.placeholderData.description_jp}</span>
          </div>
          <div>
            <span className="font-medium text-gray-700">生成プロンプト: </span>
            <span className="text-gray-600 font-mono text-xs bg-gray-100 px-2 py-1 rounded">
              {block.placeholderData.prompt_en}
            </span>
          </div>
        </div>
      </div>
    );
  };

  // 置き換えられた画像ブロックのレンダリング
  const renderReplacedImageBlock = (block: ArticleBlock) => {
    if (!block.imageData || !block.placeholderData) return null;

    const placeholderId = block.placeholderData.placeholder_id;
    const historyImages = imageHistory[placeholderId] || [];
    const isHistoryVisible = imageHistoryVisible[block.id];

    return (
      <div className="border-2 border-green-300 bg-green-50 rounded-lg p-6 mb-4 not-prose">
        <div className="flex items-center gap-3 mb-3">
          <Image className="h-6 w-6 text-green-600" aria-label="画像アイコン" />
          <div className="flex-1">
            <h4 className="font-medium text-green-900">画像 (プレースホルダーから置換済み)</h4>
            <p className="text-sm text-green-700">ID: {block.placeholderData.placeholder_id}</p>
          </div>
          <div className="flex gap-2">
            <Button 
              size="sm" 
              variant="outline" 
              className="text-purple-600 border-purple-300 hover:bg-purple-100"
              onClick={() => toggleImageHistory(block.id, placeholderId)}
              disabled={historyLoading[block.id]}
            >
              {historyLoading[block.id] ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  読込中
                </>
              ) : isHistoryVisible ? '履歴を隠す' : `他の画像 (${historyImages.length})`}
            </Button>
            <Button 
              size="sm" 
              className="bg-blue-600 hover:bg-blue-700 text-white"
              onClick={() => handleImageGeneration(block.id)}
              disabled={imageGenerationLoading[block.id]}
            >
              {imageGenerationLoading[block.id] ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-1" />
              ) : (
                <Sparkles className="h-4 w-4 mr-1" />
              )}
              新しい画像を生成
            </Button>
            <Button 
              size="sm" 
              variant="outline" 
              className="text-orange-600 border-orange-300 hover:bg-orange-100"
              onClick={() => handleImageRestore(block.id)}
            >
              <Wand2 className="h-4 w-4 mr-1" />
              プレースホルダーに戻す
            </Button>
          </div>
        </div>
        
        {/* 画像履歴表示 */}
        {isHistoryVisible && (
          <div 
            className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg"
            data-history-panel
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
          >
            <h5 className="font-medium text-purple-900 mb-2">他の生成済み画像</h5>
            {historyImages.length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {historyImages.map((image, index) => (
                  <button
                    key={image.id}
                    type="button"
                    className="relative group block focus:outline-none rounded-lg"
                    data-history-tile
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!imageApplyLoading[block.id]) applyHistoryImage(block.id, image);
                    }}
                    onMouseDown={(e) => e.stopPropagation()}
                    onPointerDown={(e) => e.stopPropagation()}
                    disabled={!!imageApplyLoading[block.id]}
                    aria-label="この履歴画像を適用"
                  >
                    <SafeImage 
                      src={image.gcs_url || image.file_path} 
                      alt={image.alt_text || `生成画像 ${index + 1}`}
                      className={`w-full h-20 object-cover rounded-lg ${
                        imageApplyLoading[block.id] ? 'opacity-50' : 'cursor-pointer'
                      }`}
                      width={80}
                      height={80}
                    />
                    <div className="absolute bottom-1 right-1 bg-black bg-opacity-60 text-white text-xs px-1 py-0.5 rounded">
                      {new Date(image.created_at).toLocaleDateString()}
                    </div>
                    <div className={`absolute inset-0 bg-blue-500 transition-all duration-200 rounded-lg flex items-center justify-center pointer-events-none ${
                      imageApplyLoading[block.id] 
                        ? 'bg-opacity-70' 
                        : 'bg-opacity-0 hover:bg-opacity-20'
                    }`}>
                      {imageApplyLoading[block.id] ? (
                        <div className="text-white font-medium flex flex-col items-center">
                          <Loader2 className="w-4 h-4 animate-spin mb-1" />
                          <span className="text-xs">適用中</span>
                        </div>
                      ) : (
                        <span className="text-white font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                          変更
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            ) : historyLoading[block.id] ? (
              <div className="text-purple-600 text-sm text-center py-4">
                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                履歴を読み込み中...
              </div>
            ) : (
              <div className="text-purple-600 text-sm text-center py-4">
                <p className="mb-2">他に生成された画像はありません</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => fetchImageHistory(placeholderId, block.id)}
                  className="text-purple-600 border-purple-300 hover:bg-purple-100"
                >
                  再読み込み
                </Button>
              </div>
            )}
          </div>
        )}

        <div className="mb-3">
          <SafeImage 
            src={block.imageData.image_url} 
            alt={block.imageData.alt_text} 
            className="max-w-full h-auto rounded-lg shadow-sm"
            style={{ maxHeight: '300px' }}
            width={600}
            height={300}
          />
        </div>
        <div className="space-y-2 text-sm">
          <div>
            <span className="font-medium text-gray-700">Alt Text: </span>
            <span className="text-gray-600">{block.imageData.alt_text}</span>
          </div>
          <div>
            <span className="font-medium text-gray-700">画像ID: </span>
            <span className="text-gray-600 font-mono text-xs bg-gray-100 px-2 py-1 rounded">
              {block.imageData.image_id}
            </span>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-lg text-gray-600">記事を読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
        return (
      <div className="space-y-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            記事の読み込み中にエラーが発生しました: {error}
          </AlertDescription>
        </Alert>
        <Button onClick={refetch} className="mt-4">
          再試行
        </Button>
          </div>
        );
  }

  if (!article) {
        return (
      <div className="space-y-6">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            記事が見つかりません。
          </AlertDescription>
        </Alert>
          </div>
        );
  }

  return (
    <div className="space-y-6 pb-24">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">記事編集</h1>
          <p className="text-gray-600 mt-1">{article.title}</p>
        </div>
        <div className="flex items-center gap-3">
          {saveError && (
            <Alert variant="destructive" className="max-w-md">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{saveError}</AlertDescription>
            </Alert>
          )}
          
          {/* 自動保存ステータス */}
          <div className="flex items-center gap-2">
            {autoSave.isAutoSaving && (
              <div className="flex items-center gap-2 text-sm text-blue-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                {autoSave.isRetrying ? `リトライ中... (${autoSave.retryCount}/3)` : '自動保存中...'}
              </div>
            )}
            {autoSave.lastSaved && !autoSave.isAutoSaving && !autoSave.error && (
              <div className="text-sm text-green-600">
                自動保存済み {autoSave.lastSaved.toLocaleTimeString('ja-JP', { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </div>
            )}
            {autoSave.error && (
              <div className="flex items-center gap-1 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" />
                <span>自動保存エラー</span>
                {autoSave.retryCount > 0 && (
                  <span className="text-xs">({autoSave.retryCount}/3 試行)</span>
                )}
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={autoSave.retryNow}
                  className="h-auto px-2 py-1 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  再試行
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={autoSave.clearError}
                  className="h-auto p-1 text-red-600 hover:text-red-700"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            )}
          </div>

          {/* HTMLエクスポートボタン */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={copyHtmlToClipboard}
              className="text-blue-600 border-blue-200 hover:bg-blue-50"
            >
              <Copy className="h-4 w-4 mr-1" />
              HTMLコピー
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={downloadHtmlFile}
              className="text-green-600 border-green-200 hover:bg-green-50"
            >
              <Download className="h-4 w-4 mr-1" />
              HTMLダウンロード
            </Button>
          </div>
          
          <Button 
            onClick={saveArticle} 
            disabled={isSaving}
            className="bg-secondary hover:bg-secondary/90"
          >
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? '保存中...' : '保存'}
          </Button>
        </div>
      </div>

      <Tabs value={editorView} onValueChange={handleEditorTabChange} className="w-full">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <TabsList className="grid w-full grid-cols-2 sm:w-auto">
            <TabsTrigger value="blocks">ブロック編集</TabsTrigger>
            <TabsTrigger value="visual">ビジュアル編集</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="blocks" className="mt-4 relative">
          <SelectionManager
            onSelectionChange={handleSelectionChange}
            blockRefs={blockRefs.current}
            className="relative w-full select-none min-h-screen"
            style={{ minHeight: '100vh' }}
          >
            <Card className="p-4 md:p-8 relative z-10">
              <ArticlePreviewStyles>

                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragStart={handleDragStart}
                  onDragOver={handleDragOver}
                  onDragEnd={handleDragEnd}
                  onDragCancel={handleDragCancel}
                >
                  <SortableContext items={blockIds} strategy={verticalListSortingStrategy}>
                    <div className="relative mx-auto max-w-4xl space-y-2">

                    {blocks.map((block, index) => {
                      const confirmationForBlock = aiConfirmations.find(c => c.blockId === block.id);
                      const dragDisabled = !!confirmationForBlock || block.isEditing;
                      const isSelected = block.isSelected;
                      const isGroupDragged = draggingBlockIds.length > 1 && draggingBlockIds.includes(block.id);

                      return (
                        <React.Fragment key={block.id}>
                          <BlockInsertButton
                            onInsertContent={handleInsertContent}
                            onAIGenerate={handleAIGenerate}
                            position={index}
                          />
                          {draggingBlockIds.length > 0 && dropIndicatorTargetId === block.id && <DropIndicator />}

                          <SortableBlock
                            id={block.id}
                            disabled={dragDisabled}
                            onNodeChange={(id, node) => {
                              blockRefs.current[id] = node;
                            }}
                          >
                            {({ attributes, listeners, setActivatorNodeRef, setNodeRef, style, isDragging, isOver }) => {
                              const dragHandleClass = cn(
                                'flex h-5 w-5 items-center justify-center rounded-md border border-transparent text-gray-400 transition focus-visible:outline-none',
                                {
                                  'cursor-not-allowed opacity-40': dragDisabled,
                                  'cursor-grab active:cursor-grabbing hover:border-purple-200 hover:text-purple-500 focus-visible:ring-2 focus-visible:ring-purple-500': !dragDisabled,
                                }
                              );

                              const combinedStyle: React.CSSProperties = {
                                ...style,
                                opacity: (isDragging || isGroupDragged) ? 0 : style?.opacity ?? 1,
                                transform: style?.transform,
                                ...(isDragging || isGroupDragged ? {
                                  visibility: 'hidden',
                                  height: 0,
                                  minHeight: 0,
                                  padding: 0,
                                  margin: 0,
                                  overflow: 'hidden'
                                } : {})
                              };

                              return (
                                <div
                                  ref={setNodeRef}
                                  style={combinedStyle}
                                  className={cn(
                                    'group relative flex items-start gap-3 rounded-lg border border-transparent px-3 py-1 transition-all duration-150',
                                    {
                                      'bg-blue-50': hoveredBlockId === block.id && !block.isEditing && !confirmationForBlock,
                                      'border-blue-400 bg-blue-50/70 shadow-inner': isSelected && !isDragging && !confirmationForBlock,
                                      'bg-white': !!confirmationForBlock,
                                      'ring-2 ring-purple-300/90 bg-white shadow-xl': isDragging,
                                      'ring-2 ring-purple-200/70 bg-purple-50/80 shadow-lg': isGroupDragged && !isDragging,
                                      'ring-2 ring-purple-200/70 bg-purple-50/70': isOver && !isDragging && !confirmationForBlock,
                                    },
                                  )}
                                  onPointerDown={handleBlockPointerDown(block.id)}
                                  onMouseEnter={() => !confirmationForBlock && setHoveredBlockId(block.id)}
                                  onMouseLeave={() => setHoveredBlockId(null)}
                                  data-block-id={block.id}
                                  data-selected={isSelected.toString()}
                                >
                                  <div className="pointer-events-none absolute left-0 top-1/2 flex -translate-y-1/2 items-center gap-2 pl-1 pr-3">
                                    <button
                                      type="button"
                                      ref={setActivatorNodeRef}
                                      {...attributes}
                                      {...listeners}
                                      className={dragHandleClass}
                                      aria-label="ブロックをドラッグして並び替える"
                                      disabled={dragDisabled}
                                      data-interactive="true"
                                      style={{ pointerEvents: 'auto' }}
                                    >
                                      <GripDots />
                                    </button>
                                  </div>

                                  <div className="ml-9 flex-1" data-allow-selection="true">
                                    {confirmationForBlock ? (
                                      <div className="notion-card border border-blue-100/80 bg-white/95 p-4 my-2 rounded-xl shadow-[0_15px_35px_-25px_rgba(99,102,241,0.55)] transition-all duration-300">
                                        <h3 className="text-lg font-semibold text-blue-800 mb-3">AIによる修正提案</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                          <div>
                                            <h4 className="font-bold mb-2 text-sm text-gray-500">変更前</h4>
                                            <ArticlePreviewStyles>
                                              <div
                                                className="text-sm border p-3 rounded-md bg-gray-50 max-h-48 overflow-y-auto prose-sm"
                                                dangerouslySetInnerHTML={{ __html: confirmationForBlock.originalContent }}
                                              />
                                            </ArticlePreviewStyles>
                                          </div>
                                          <div>
                                            <h4 className="font-bold mb-2 text-sm text-blue-600">変更後</h4>
                                            <ArticlePreviewStyles>
                                              <div
                                                className="text-sm border border-blue-200 p-3 rounded-md bg-blue-50 max-h-48 overflow-y-auto prose-sm"
                                                dangerouslySetInnerHTML={{ __html: confirmationForBlock.newContent }}
                                              />
                                            </ArticlePreviewStyles>
                                          </div>
                                        </div>
                                        <div className="flex justify-end items-center gap-2 mt-4">
                                          {aiEditingLoading && <Bot className="w-4 h-4 animate-spin text-blue-600" />}
                                          <Button variant="outline" size="sm" onClick={() => handleRegenerate(block.id)} disabled={aiEditingLoading}>再生成</Button>
                                          <Button variant="ghost" size="sm" onClick={() => handleCancel(block.id)} disabled={aiEditingLoading}>キャンセル</Button>
                                          <Button size="sm" onClick={() => handleApprove(block.id)} disabled={aiEditingLoading}>承認して反映</Button>
                                        </div>
                                      </div>
                                    ) : block.isEditing ? (
                                      <div className="notion-editing-panel border border-blue-100 bg-white/95 rounded-xl p-3 shadow-[0_12px_25px_-20px_rgba(99,102,241,0.45)]">
                                        <Textarea
                                          defaultValue={block.content}
                                          onBlur={(e) => saveBlock(block.id, e.target.value)}
                                          className="w-full p-2 border rounded resize-y min-h-[80px]"
                                          autoFocus
                                        />
                                        <div className="flex justify-end gap-2 mt-2">
                                          <Button size="sm" variant="outline" onClick={() => cancelEditing(block.id)}>キャンセル</Button>
                                          <Button
                                            size="sm"
                                            onClick={(e) => {
                                              const textarea = (e.target as HTMLElement).closest('div')?.querySelector('textarea');
                                              if (textarea) saveBlock(block.id, textarea.value);
                                            }}
                                          >
                                            保存
                                          </Button>
                                        </div>
                                      </div>
                                    ) : (
                                      <Popover>
                                        <PopoverTrigger asChild>
                                          <div className="w-full cursor-pointer rounded-md p-1 hover:bg-gray-100/50" data-block-content="true" data-allow-selection="true">
                                            {block.type === 'image_placeholder'
                                              ? renderImagePlaceholderBlock(block)
                                              : block.type === 'replaced_image'
                                                ? renderReplacedImageBlock(block)
                                                : renderBlockContent(block)}
                                          </div>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-48 p-1" side="right" align="start" data-interactive="true">
                                          <div className="space-y-1">
                                            {block.type === 'image_placeholder' ? (
                                              <>
                                                <Button
                                                  variant="ghost"
                                                  className="w-full justify-start"
                                                  size="sm"
                                                  onClick={() => triggerFileUpload(block.id)}
                                                  disabled={imageUploadLoading[block.id]}
                                                >
                                                  {imageUploadLoading[block.id] ? (
                                                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-gray-600" />
                                                  ) : (
                                                    <Upload className="w-4 h-4 mr-2" />
                                                  )}
                                                  画像をアップロード
                                                </Button>
                                                <Button
                                                  variant="ghost"
                                                  className="w-full justify-start"
                                                  size="sm"
                                                  onClick={() => handleImageGeneration(block.id)}
                                                  disabled={imageGenerationLoading[block.id]}
                                                >
                                                  {imageGenerationLoading[block.id] ? (
                                                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-gray-600" />
                                                  ) : (
                                                    <Sparkles className="w-4 h-4 mr-2" />
                                                  )}
                                                  AIで画像を生成
                                                </Button>
                                                <Button
                                                  variant="ghost"
                                                  className="w-full justify-start text-red-500 hover:text-red-600"
                                                  size="sm"
                                                  onClick={() => deleteBlock(block.id)}
                                                >
                                                  <Trash2 className="w-4 h-4 mr-2" /> 削除
                                                </Button>
                                              </>
                                            ) : block.type === 'replaced_image' ? (
                                              <>
                                                <Button
                                                  variant="ghost"
                                                  className="w-full justify-start"
                                                  size="sm"
                                                  onClick={() => handleImageRestore(block.id)}
                                                  disabled={historyLoading[block.id]}
                                                >
                                                  {historyLoading[block.id] ? (
                                                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-gray-600" />
                                                  ) : (
                                                    <Undo className="w-4 h-4 mr-2" />
                                                  )}
                                                  元の画像に戻す
                                                </Button>
                                                <Button
                                                  variant="ghost"
                                                  className="w-full justify-start"
                                                  size="sm"
                                                  onClick={() => triggerFileUpload(block.id)}
                                                  disabled={imageUploadLoading[block.id]}
                                                >
                                                  {imageUploadLoading[block.id] ? (
                                                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-gray-600" />
                                                  ) : (
                                                    <Upload className="w-4 h-4 mr-2" />
                                                  )}
                                                  別の画像に変更
                                                </Button>
                                                <Button variant="ghost" className="w-full justify-start text-red-500 hover:text-red-600" size="sm" onClick={() => deleteBlock(block.id)}><Trash2 className="w-4 h-4 mr-2" /> 削除</Button>
                                              </>
                                            ) : (
                                              <>
                                                <Button variant="ghost" className="w-full justify-start" size="sm" onClick={() => openAiModal('single', block)}><Bot className="w-4 h-4 mr-2" /> AIに修正を依頼</Button>
                                                <Button variant="ghost" className="w-full justify-start" size="sm" onClick={() => startEditing(block.id)}><Edit className="w-4 h-4 mr-2" /> 自分で修正</Button>
                                                <Button variant="ghost" className="w-full justify-start text-red-500 hover:text-red-600" size="sm" onClick={() => deleteBlock(block.id)}><Trash2 className="w-4 h-4 mr-2" /> 削除</Button>
                                              </>
                                            )}
                                          </div>
                                        </PopoverContent>
                                      </Popover>
                                    )}
                                  </div>
                                </div>
                              );
                            }}
                          </SortableBlock>
                        </React.Fragment>
                      );
                    })}

                    {draggingBlockIds.length > 0 && showDropIndicatorAtEnd && <DropIndicator />}

                    <BlockInsertButton
                      onInsertContent={handleInsertContent}
                      onAIGenerate={handleAIGenerate}
                      position={blocks.length}
                    />
                    </div>
                  </SortableContext>

                <DragOverlay dropAnimation={{ duration: 160, easing: 'cubic-bezier(0.2, 0.7, 0.3, 1)' }}>
                  {overlayBlocks.length > 0 ? (
                    <div className="pointer-events-none max-w-4xl">
                      <ArticlePreviewStyles>
                        <div className="relative pointer-events-none">
                          {overlayBlocks.slice(0, Math.min(5, overlayBlocks.length)).map((block, index) => (
                            <div
                              key={`overlay-${block.id}-${index}`}
                              className="pointer-events-none rounded-lg border-2 border-purple-400 bg-white px-5 py-4 shadow-2xl"
                              style={{
                                transform: `translate(${index * 8}px, ${index * 6}px)`,
                                opacity: 1 - (index * 0.15)
                              }}
                            >
                              <div className="mb-2 flex items-center justify-between text-[11px] font-semibold tracking-wide text-purple-600">
                                <span>{draggingBlockIds.length > 1 ? `選択 ${index + 1}` : 'ドラッグ中'}</span>
                                {draggingBlockIds.length > 1 && index === 0 && (
                                  <span className="rounded-full bg-purple-200 px-2 py-0.5 text-[10px] text-purple-800 font-bold">
                                    {draggingBlockIds.length} 個選択
                                  </span>
                                )}
                              </div>
                              <div className="pointer-events-none">
                                {renderDragOverlayBlock(block)}
                              </div>
                            </div>
                          ))}
                        </div>
                      </ArticlePreviewStyles>
                      {overlayBlocks.length > 5 && (
                        <div className="mt-3 text-center text-xs text-purple-600 font-semibold">
                          他 {overlayBlocks.length - 5} 個
                        </div>
                      )}
                    </div>
                  ) : null}
                </DragOverlay>
              </DndContext>

            </ArticlePreviewStyles>
            </Card>
          </SelectionManager>
        </TabsContent>

        <TabsContent value="visual" className="mt-4">
          <Card className="p-4 md:p-6">
            <ArticlePreviewStyles>
              <RichTextVisualEditor value={visualHtml} onChange={handleVisualEditorChange} />
            </ArticlePreviewStyles>
          </Card>
        </TabsContent>
      </Tabs>
      
      {/* 記事メタ情報 */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">記事情報</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="font-medium text-gray-600">作成日:</span>
            <p className="text-gray-800">{new Date(article.created_at || '').toLocaleDateString('ja-JP')}</p>
          </div>
          <div>
            <span className="font-medium text-gray-600">ステータス:</span>
            <p className="text-gray-800">{article.status}</p>
          </div>
          <div>
            <span className="font-medium text-gray-600">ターゲット:</span>
            <p className="text-gray-800">{article.target_audience || '未設定'}</p>
          </div>
        </div>
      </Card>

      {/* AI Confirmation Toolbar */}
      {editorView === 'blocks' && aiConfirmations.length > 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
          <Card className="p-2 flex items-center gap-3 shadow-lg border-2 border-blue-500 bg-white">
            <span className="text-sm font-medium pl-2 pr-1">{aiConfirmations.length}件のAI修正案</span>
            <Button size="sm" onClick={handleApproveAll}>全て承認</Button>
            <Button size="sm" variant="outline" onClick={handleCancelAll}>全てキャンセル</Button>
          </Card>
        </div>
      )}

      {/* Bulk Selection Toolbar */}
      {editorView === 'blocks' && selectedBlocksCount > 0 && aiConfirmations.length === 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
          <Card className="p-2 flex items-center gap-3 shadow-lg border-2 border-blue-200">
            <span className="text-sm font-medium pl-2 pr-1">{selectedBlocksCount}件選択中</span>
            <Button size="sm" onClick={() => openAiModal('bulk')}>
              <Bot className="w-4 h-4 mr-2" /> AIで一括修正
            </Button>
            <Button size="sm" variant="destructive" onClick={handleBulkDelete}>
              <Trash2 className="w-4 h-4 mr-2" /> 選択項目を削除
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setBlocks(prev => prev.map(b => ({ ...b, isSelected: false })))}>
              <X className="w-4 h-4" />
            </Button>
          </Card>
        </div>
      )}

      {/* AI編集モーダル */}
      <Dialog open={isAiModalOpen} onOpenChange={setIsAiModalOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>
              {aiEditMode === 'bulk' ? `${selectedBlocksCount}件のブロックをAIで編集` : 'AIでブロックを編集'}
            </DialogTitle>
            <DialogDescription>
              {aiEditMode === 'bulk'
                ? "選択したすべてのブロックに同じ編集指示を適用します。"
                : "AIへの指示を入力してください。元のブロック内容を元に新しい内容を生成します。"
              }
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {aiEditMode === 'single' && currentBlockForAi && (
              <div>
                <p className="text-sm font-medium mb-2">元のブロック</p>
                <div className="p-3 rounded-md border bg-gray-50 text-sm max-h-32 overflow-y-auto"
                  dangerouslySetInnerHTML={{ __html: currentBlockForAi.content }}
                />
              </div>
            )}
            
            <div>
              <p className="text-sm font-medium mb-2">編集指示</p>
              <div className="flex flex-wrap gap-2 mb-2">
                <Button size="sm" variant="outline" onClick={() => setAiInstruction("もっとカジュアルな文体に")}>カジュアルに</Button>
                <Button size="sm" variant="outline" onClick={() => setAiInstruction("もっと専門的で詳細な説明に")}>専門的に</Button>
                <Button size="sm" variant="outline" onClick={() => setAiInstruction("文章の量を約半分に要約して")}>短く</Button>
                <Button size="sm" variant="outline" onClick={() => setAiInstruction("より多くの具体例を加えて文章を膨らませて")}>長く</Button>
              </div>
              <Textarea
                placeholder="例：小学生にもわかるように、もっと簡単な言葉で説明してください。"
                value={aiInstruction}
                onChange={(e) => setAiInstruction(e.target.value)}
                className="min-h-[100px]"
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">キャンセル</Button>
            </DialogClose>
            <Button type="button" onClick={runAiEdit} disabled={aiEditingLoading || !aiInstruction}>
              {aiEditingLoading && <Bot className="mr-2 h-4 w-4 animate-spin" />}
              {aiEditingLoading ? "生成中..." : aiEditMode === 'bulk' ? '一括修正を実行' : 'AIに修正を依頼'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* コンテンツ選択ダイアログ */}
      <ContentSelectorDialog
        isOpen={contentSelectorOpen}
        onClose={() => setContentSelectorOpen(false)}
        onSelectContent={handleSelectContentType}
        position={insertPosition}
      />

      {/* 目次作成ダイアログ */}
      <TableOfContentsDialog
        isOpen={tocDialogOpen}
        onClose={() => setTocDialogOpen(false)}
        onInsertToc={handleInsertToc}
        htmlContent={blocksToHtml(blocks)}
      />

      {/* 見出しレベル選択ダイアログ */}
      <HeadingLevelDialog
        isOpen={headingLevelDialogOpen}
        onClose={() => setHeadingLevelDialogOpen(false)}
        onSelectHeading={handleSelectHeadingLevel}
        position={insertPosition}
      />

      {/* AIコンテンツ生成ダイアログ */}
      <AIContentGenerationDialog
        isOpen={aiContentDialogOpen}
        onClose={() => setAiContentDialogOpen(false)}
        onGenerate={handleAIContentGenerated}
        position={insertPosition}
        getToken={getToken}
        articleId={articleId}
        articleHtml={article?.content}
      />
    </div>
  );
} 
