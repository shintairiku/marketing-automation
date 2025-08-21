'use client';

import React, { useCallback, useMemo } from 'react';
import { useEffect, useState } from 'react';
import NextImage from 'next/image';
import { AlertCircle, Bot, Copy, Download, Edit, Image, Save, Sparkles, Trash2, Upload, Wand2, X } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Textarea } from '@/components/ui/textarea';
import { useArticleDetail } from '@/hooks/useArticles';
import { useAutoSave } from '@/hooks/useAutoSave';
import { cn } from "@/utils/cn";
import { useAuth } from '@clerk/nextjs';

import ArticlePreviewStyles from '../new-article/component/ArticlePreviewStyles';

import BlockInsertButton from './components/BlockInsertButton';
import ContentSelectorDialog from './components/ContentSelectorDialog';
import TableOfContentsDialog from './components/TableOfContentsDialog';

interface EditArticlePageProps {
  articleId: string;
}

interface ArticleBlock {
  id: string;
  type: 'h1' | 'h2' | 'h3' | 'p' | 'ul' | 'ol' | 'li' | 'img' | 'image_placeholder' | 'replaced_image' | 'div';
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
  onClick?: () => void;
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
  
  // 画像関連の状態
  const [imageUploadLoading, setImageUploadLoading] = useState<{ [blockId: string]: boolean }>({});
  const [imageGenerationLoading, setImageGenerationLoading] = useState<{ [blockId: string]: boolean }>({});
  const [imageHistoryVisible, setImageHistoryVisible] = useState<{ [blockId: string]: boolean }>({});
  const [imageHistory, setImageHistory] = useState<{ [placeholderId: string]: any[] }>({});
  
  // AI編集モーダル用state
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [aiInstruction, setAiInstruction] = useState("");
  const [lastAiInstruction, setLastAiInstruction] = useState(""); // 再生成用
  const [currentBlockForAi, setCurrentBlockForAi] = useState<ArticleBlock | null>(null);
  const [aiEditMode, setAiEditMode] = useState<'single' | 'bulk'>('single');

  const [aiConfirmations, setAiConfirmations] = useState<AiConfirmationState[]>([]);

  // コンテンツ挿入関連のstate
  const [contentSelectorOpen, setContentSelectorOpen] = useState(false);
  const [tocDialogOpen, setTocDialogOpen] = useState(false);
  const [insertPosition, setInsertPosition] = useState<number>(0);

  const selectedBlocksCount = useMemo(() => blocks.filter(b => b.isSelected).length, [blocks]);

  // void要素の判定
  const isVoidElement = (tagName: string): boolean => {
    const voidElements = ['br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'];
    return voidElements.includes(tagName.toLowerCase());
  };

  // HTMLコンテンツをブロックに分割（画像プレースホルダー対応）
  const parseHtmlToBlocks = useCallback((html: string): ArticleBlock[] => {
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

  // コンテンツタイプ選択の処理
  const handleSelectContentType = (type: string) => {
    if (type === 'table-of-contents') {
      setTocDialogOpen(true);
    }
  };

  // 目次の挿入
  const handleInsertToc = (tocHtml: string) => {
    const newBlock: ArticleBlock = {
      id: `toc-${Date.now()}`,
      type: 'div' as any, // 目次はdivとして扱う
      content: tocHtml,
      isEditing: false,
      isSelected: false
    };

    const newBlocks = [...blocks];
    newBlocks.splice(insertPosition, 0, newBlock);
    setBlocks(newBlocks);
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
      
      // ブロックを置き換えられた画像タイプに更新
      setBlocks(prev => prev.map(b => 
        b.id === blockId 
          ? { 
              ...b, 
              type: 'replaced_image', 
              content: `<img src="${result.image_url}" alt="${result.alt_text}" class="article-image" data-placeholder-id="${placeholderData.placeholder_id}" data-image-id="${result.image_id}" />`,
              imageData: {
                image_id: result.image_id,
                image_url: result.image_url,
                alt_text: result.alt_text,
              }
            }
          : b
      ));

      alert('画像が生成されました！保存ボタンを押すか、別の画像を生成することもできます。');
    } catch (error) {
      console.error('画像生成エラー:', error);
      alert('画像の生成に失敗しました。');
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
      
      // ブロックをプレースホルダータイプに戻す（元のプレースホルダーデータを保持）
      setBlocks(prev => prev.map(b => 
        b.id === blockId 
          ? { 
              ...b, 
              type: 'image_placeholder', 
              content: result.updated_content.match(/<!-- IMAGE_PLACEHOLDER: [^>]+ -->/)?.[0] || b.content,
              // placeholderDataは保持する
              imageData: undefined
            }
          : b
      ));

      alert('画像がプレースホルダーに戻されました！');
    } catch (error) {
      console.error('画像復元エラー:', error);
      alert('画像の復元に失敗しました。');
    }
  };

  // 画像履歴を取得
  const fetchImageHistory = async (placeholderId: string) => {
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
        console.warn('画像履歴の取得に失敗しました');
        return [];
      }
    } catch (error) {
      console.error('画像履歴取得エラー:', error);
      return [];
    }
  };

  // 過去の画像を選択してプレースホルダーに適用
  const applyHistoryImage = async (blockId: string, imageData: any) => {
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
      setBlocks(prev => prev.map(b => 
        b.id === blockId 
          ? { 
              ...b, 
              type: 'replaced_image', 
              content: result.updated_content.match(new RegExp(`<img[^>]*data-placeholder-id="${block.placeholderData!.placeholder_id}"[^>]*>`))?.[0] || b.content,
              imageData: {
                image_id: result.image_id,
                image_url: imageData.gcs_url || imageData.file_path,
                alt_text: imageData.alt_text || block.placeholderData!.description_jp,
              }
            }
          : b
      ));

      // 画像履歴を非表示にする
      setImageHistoryVisible(prev => ({ ...prev, [blockId]: false }));
      
      alert('過去の画像が適用されました！');
    } catch (error) {
      console.error('画像適用エラー:', error);
      alert('画像の適用に失敗しました。');
    }
  };

  // 画像履歴の表示切り替え
  const toggleImageHistory = async (blockId: string, placeholderId: string) => {
    const isVisible = imageHistoryVisible[blockId];
    
    if (!isVisible) {
      // 履歴を表示する場合は、データを取得
      await fetchImageHistory(placeholderId);
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

  // コンテンツ抽出関数：UI状態を除外して実際のコンテンツのみを抽出
  const extractContent = useCallback((blocks: ArticleBlock[]) => {
    return blocks.map(block => ({
      id: block.id,
      type: block.type,
      content: block.content,
      placeholderData: block.placeholderData,
      imageData: block.imageData
    }));
  }, []);

  // 自動保存フックの設定
  const autoSave = useAutoSave(blocks, autoSaveArticle, {
    delay: 2000, // 2秒のデバウンス
    enabled: autoSaveEnabled && !!article && blocks.length > 0,
    maxRetries: 3, // 最大3回リトライ
    retryDelay: 1000, // 1秒後にリトライ開始
    excludeKeys: ['isEditing', 'isSelected'], // UI状態を除外
    contentExtractor: (blocks: ArticleBlock[]) => JSON.stringify(extractContent(blocks)), // コンテンツのみを抽出
  });

  // 自動保存の制御: 特定の操作中は無効化
  useEffect(() => {
    // AI編集中、手動保存中、画像関連の操作中は自動保存を無効化
    const hasAnyLoading = aiEditingLoading || 
                         isSaving || 
                         Object.values(imageUploadLoading).some(loading => loading) ||
                         Object.values(imageGenerationLoading).some(loading => loading);
    
    if (hasAnyLoading) {
      setAutoSaveEnabled(false);
    } else {
      // 操作が完了したら少し遅延してから自動保存を再有効化
      const timer = setTimeout(() => {
        setAutoSaveEnabled(true);
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [aiEditingLoading, isSaving, imageUploadLoading, imageGenerationLoading]);

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

  // 画像プレースホルダーブロックのレンダリング
  const renderImagePlaceholderBlock = (block: ArticleBlock) => {
    if (!block.placeholderData) return null;

    const placeholderId = block.placeholderData.placeholder_id;
    const historyImages = imageHistory[placeholderId] || [];
    const isHistoryVisible = imageHistoryVisible[block.id];

    return (
      <div className="border-2 border-dashed border-blue-300 bg-blue-50 rounded-lg p-6 mb-4 not-prose">
        <div className="flex items-center gap-3 mb-3">
          <Image className="h-6 w-6 text-blue-600" />
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
            >
              {isHistoryVisible ? '履歴を隠す' : `履歴 (${historyImages.length})`}
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
          <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
            <h5 className="font-medium text-purple-900 mb-2">生成済み画像履歴</h5>
            {historyImages.length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {historyImages.map((image, index) => (
                  <div key={image.id} className="relative group">
                    <SafeImage 
                      src={image.gcs_url || image.file_path} 
                      alt={image.alt_text || `生成画像 ${index + 1}`}
                      className="w-full h-24 object-cover rounded-lg cursor-pointer hover:opacity-80 transition-opacity"
                      onClick={() => applyHistoryImage(block.id, image)}
                      width={100}
                      height={96}
                    />
                    <div className="absolute bottom-1 right-1 bg-black bg-opacity-60 text-white text-xs px-1 py-0.5 rounded">
                      {new Date(image.created_at).toLocaleDateString()}
                    </div>
                    <div className="absolute inset-0 bg-blue-500 bg-opacity-0 hover:bg-opacity-20 transition-all duration-200 rounded-lg flex items-center justify-center">
                      <span className="text-white font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                        選択
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-purple-600 text-sm">まだ画像が生成されていません</p>
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
          <Image className="h-6 w-6 text-green-600" />
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
            >
              {isHistoryVisible ? '履歴を隠す' : `他の画像 (${historyImages.length})`}
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
          <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
            <h5 className="font-medium text-purple-900 mb-2">他の生成済み画像</h5>
            {historyImages.length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {historyImages.map((image, index) => (
                  <div key={image.id} className="relative group">
                    <SafeImage 
                      src={image.gcs_url || image.file_path} 
                      alt={image.alt_text || `生成画像 ${index + 1}`}
                      className="w-full h-20 object-cover rounded-lg cursor-pointer hover:opacity-80 transition-opacity"
                      onClick={() => applyHistoryImage(block.id, image)}
                      width={80}
                      height={80}
                    />
                    <div className="absolute bottom-1 right-1 bg-black bg-opacity-60 text-white text-xs px-1 py-0.5 rounded">
                      {new Date(image.created_at).toLocaleDateString()}
                    </div>
                    <div className="absolute inset-0 bg-blue-500 bg-opacity-0 hover:bg-opacity-20 transition-all duration-200 rounded-lg flex items-center justify-center">
                      <span className="text-white font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                        変更
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-purple-600 text-sm">他に生成された画像はありません</p>
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

      {/* Notion風エディタエリア */}
      <Card className="p-4 md:p-8">
        <ArticlePreviewStyles>
          <div className="max-w-4xl mx-auto space-y-2">
            {blocks.map((block, index) => {
              const confirmationForBlock = aiConfirmations.find(c => c.blockId === block.id);
              return (
              <React.Fragment key={block.id}>
                {/* ブロック間の挿入ボタン */}
                <BlockInsertButton
                  onInsertContent={handleInsertContent}
                  position={index}
                />
                
                <div
                className={cn(
                  "group relative flex items-start gap-3 py-1 pr-2 pl-10 rounded-md transition-colors",
                  { 
                    "bg-blue-50": hoveredBlockId === block.id && !block.isEditing && !confirmationForBlock,
                    "bg-white": !!confirmationForBlock
                  }
                )}
                onMouseEnter={() => !confirmationForBlock && setHoveredBlockId(block.id)}
                onMouseLeave={() => setHoveredBlockId(null)}
              >
                <div className="absolute left-2 top-3 transition-opacity opacity-20 group-hover:opacity-100">
                  <Checkbox
                    checked={block.isSelected}
                    onCheckedChange={(checked) => handleSelectionToggle(block.id, checked)}
                    disabled={!!confirmationForBlock}
                  />
                </div>

                <div className="flex-1 w-full">
                  {confirmationForBlock ? (
                    <div className="border-2 border-blue-200 rounded-lg p-4 my-2 transition-all duration-300 bg-white shadow-md">
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
                    <div>
                      <Textarea
                        defaultValue={block.content}
                        onBlur={(e) => saveBlock(block.id, e.target.value)}
                        className="w-full p-2 border rounded resize-y min-h-[80px]"
                        autoFocus
                      />
                      <div className="flex justify-end gap-2 mt-2">
                         <Button size="sm" variant="outline" onClick={() => cancelEditing(block.id)}>キャンセル</Button>
                         <Button size="sm" onClick={(e) => {
                           const textarea = (e.target as HTMLElement).closest('div')?.querySelector('textarea');
                           if(textarea) saveBlock(block.id, textarea.value);
                         }}>保存</Button>
                      </div>
                    </div>
                  ) : (
                    <Popover>
                      <PopoverTrigger asChild>
                        <div className="w-full cursor-pointer p-1 rounded-md hover:bg-gray-100/50">
                          {block.type === 'image_placeholder' ? (
                            renderImagePlaceholderBlock(block)
                          ) : block.type === 'replaced_image' ? (
                            renderReplacedImageBlock(block)
                          ) : (
                            renderBlockContent(block)
                          )}
                        </div>
                      </PopoverTrigger>
                    <PopoverContent className="w-48 p-1" side="right" align="start">
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
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2" />
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
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2" />
                              ) : (
                                <Sparkles className="w-4 h-4 mr-2" />
                              )}
                              AI画像生成
                            </Button>
                            <Button variant="ghost" className="w-full justify-start text-red-500 hover:text-red-600" size="sm" onClick={() => deleteBlock(block.id)}>
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
                            >
                              <Wand2 className="w-4 h-4 mr-2" />
                              プレースホルダーに戻す
                            </Button>
                            <Button 
                              variant="ghost" 
                              className="w-full justify-start" 
                              size="sm"
                              onClick={() => triggerFileUpload(block.id)}
                              disabled={imageUploadLoading[block.id]}
                            >
                              {imageUploadLoading[block.id] ? (
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2" />
                              ) : (
                                <Upload className="w-4 h-4 mr-2" />
                              )}
                              別の画像に変更
                            </Button>
                            <Button variant="ghost" className="w-full justify-start text-red-500 hover:text-red-600" size="sm" onClick={() => deleteBlock(block.id)}>
                              <Trash2 className="w-4 h-4 mr-2" /> 削除
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button variant="ghost" className="w-full justify-start" size="sm" onClick={() => openAiModal('single', block)}>
                              <Bot className="w-4 h-4 mr-2" /> AIに修正を依頼
                            </Button>
                            <Button variant="ghost" className="w-full justify-start" size="sm" onClick={() => startEditing(block.id)}>
                              <Edit className="w-4 h-4 mr-2" /> 自分で修正
                            </Button>
                            <Button variant="ghost" className="w-full justify-start text-red-500 hover:text-red-600" size="sm" onClick={() => deleteBlock(block.id)}>
                              <Trash2 className="w-4 h-4 mr-2" /> 削除
                            </Button>
                          </>
                        )}
                      </div>
                    </PopoverContent>
                  </Popover>
                )}
              </div>
            </div>
              </React.Fragment>
            );
          })}
          
          {/* 最後のブロックの後に挿入ボタンを追加 */}
          <BlockInsertButton
            onInsertContent={handleInsertContent}
            position={blocks.length}
          />
        </div>
        </ArticlePreviewStyles>
      </Card>
      
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
      {aiConfirmations.length > 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
          <Card className="p-2 flex items-center gap-3 shadow-lg border-2 border-blue-500 bg-white">
            <span className="text-sm font-medium pl-2 pr-1">{aiConfirmations.length}件のAI修正案</span>
            <Button size="sm" onClick={handleApproveAll}>全て承認</Button>
            <Button size="sm" variant="outline" onClick={handleCancelAll}>全てキャンセル</Button>
          </Card>
        </div>
      )}

      {/* Bulk Selection Toolbar */}
      {selectedBlocksCount > 0 && aiConfirmations.length === 0 && (
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
    </div>
  );
} 