'use client';

import React, { useCallback, useMemo } from 'react';
import { useEffect, useState } from 'react';
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
import { cn } from "@/utils/cn";
import { useAuth } from '@clerk/nextjs';

interface EditArticlePageProps {
  articleId: string;
}

interface ArticleBlock {
  id: string;
  type: 'h1' | 'h2' | 'h3' | 'p' | 'ul' | 'ol' | 'li' | 'image_placeholder';
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
}

interface AiConfirmationState {
  blockId: string;
  originalType: ArticleBlock['type'];
  originalContent: string;
  newContent: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function EditArticlePage({ articleId }: EditArticlePageProps) {
  const { getToken } = useAuth();
  const { article, loading, error, refetch } = useArticleDetail(articleId);
  const [blocks, setBlocks] = useState<ArticleBlock[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [hoveredBlockId, setHoveredBlockId] = useState<string | null>(null);
  const [aiEditingLoading, setAiEditingLoading] = useState(false);
  
  // 画像関連の状態
  const [imageUploadLoading, setImageUploadLoading] = useState<{ [blockId: string]: boolean }>({});
  const [imageGenerationLoading, setImageGenerationLoading] = useState<{ [blockId: string]: boolean }>({});
  
  // AI編集モーダル用state
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [aiInstruction, setAiInstruction] = useState("");
  const [lastAiInstruction, setLastAiInstruction] = useState(""); // 再生成用
  const [currentBlockForAi, setCurrentBlockForAi] = useState<ArticleBlock | null>(null);
  const [aiEditMode, setAiEditMode] = useState<'single' | 'bulk'>('single');

  const [aiConfirmations, setAiConfirmations] = useState<AiConfirmationState[]>([]);

  const selectedBlocksCount = useMemo(() => blocks.filter(b => b.isSelected).length, [blocks]);

  // void要素の判定
  const isVoidElement = (tagName: string): boolean => {
    const voidElements = ['br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'];
    return voidElements.includes(tagName.toLowerCase());
  };

  // HTMLコンテンツをブロックに分割（画像プレースホルダー対応）
  const parseHtmlToBlocks = (html: string): ArticleBlock[] => {
    const blocks: ArticleBlock[] = [];
    let blockIndex = 0;
    
    // 画像プレースホルダーとHTML要素を混在した状態で処理
    // HTMLを改行で分割し、各行を個別に処理
    const segments = html.split('\n').filter(line => line.trim() !== '');
    
    for (const segment of segments) {
      const trimmedSegment = segment.trim();
      
      // 画像プレースホルダーかチェック
      const placeholderMatch = trimmedSegment.match(/<!-- IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+) -->/);
      if (placeholderMatch) {
        const [fullMatch, placeholderId, descriptionJp, promptEn] = placeholderMatch;
        
        blocks.push({
          id: `placeholder-${blockIndex++}`,
          type: 'image_placeholder',
          content: fullMatch,
          isEditing: false,
          isSelected: false,
          placeholderData: {
            placeholder_id: placeholderId.trim(),
            description_jp: descriptionJp.trim(),
            prompt_en: promptEn.trim(),
            alt_text: descriptionJp.trim(),
          },
        });
        continue;
      }
      
      // HTML要素を解析
      const parser = new DOMParser();
      const doc = parser.parseFromString(`<div>${trimmedSegment}</div>`, 'text/html');
      const container = doc.body.firstElementChild;
      
      if (container && container.children.length > 0) {
        // コンテナ内の要素を順番に処理
        Array.from(container.children).forEach(element => {
          const tagName = element.tagName.toLowerCase();
          
          blocks.push({
            id: `block-${blockIndex++}`,
            type: tagName as ArticleBlock['type'],
            content: isVoidElement(tagName) ? '' : element.innerHTML, // void要素は空文字
            isEditing: false,
            isSelected: false,
          });
        });
      } else if (container && container.textContent?.trim()) {
        // テキストのみの場合
        blocks.push({
          id: `block-${blockIndex++}`,
          type: 'p',
          content: container.textContent.trim(),
          isEditing: false,
          isSelected: false,
        });
      } else {
        // 直接HTML要素の場合
        const directParser = new DOMParser();
        const directDoc = directParser.parseFromString(trimmedSegment, 'text/html');
        const directElement = directDoc.body.firstElementChild;
        
        if (directElement) {
          const tagName = directElement.tagName.toLowerCase();
          
          blocks.push({
            id: `block-${blockIndex++}`,
            type: tagName as ArticleBlock['type'],
            content: isVoidElement(tagName) ? '' : directElement.innerHTML, // void要素は空文字
            isEditing: false,
            isSelected: false,
          });
        }
      }
    }
    
    return blocks;
  };

  // ブロックをHTMLに戻す（画像プレースホルダー対応）
  const blocksToHtml = (blocks: ArticleBlock[]): string => {
    return blocks.map(block => {
      if (block.type === 'image_placeholder') {
        // 画像プレースホルダーはコメント形式でそのまま出力
        return block.content;
      }
      
      // void要素は自己完結タグとして出力
      if (isVoidElement(block.type)) {
        return `<${block.type} />`;
      }
      
      return `<${block.type}>${block.content}</${block.type}>`;
    }).join('\n');
  };

  // 記事データが更新されたときにブロックを再構築
  useEffect(() => {
    if (article?.content) {
      setBlocks(parseHtmlToBlocks(article.content));
    }
  }, [article]);

  const handleSelectionToggle = (blockId: string, checked: boolean | 'indeterminate') => {
    setBlocks(prev => 
      prev.map(block => 
        block.id === blockId ? { ...block, isSelected: !!checked } : block
      )
    );
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
    setCurrentBlockForAi(mode === 'single' ? block || null : null);
    setAiInstruction("");
    setIsAiModalOpen(true);
  };
  
  // AI 編集実行
  const runAiEdit = async () => {
    const instruction = aiInstruction;
    if (!instruction) return;
    
    const targets = aiEditMode === 'bulk' 
      ? blocks.filter(b => b.isSelected)
      : currentBlockForAi ? [currentBlockForAi] : [];

    if (targets.length === 0) return;

    setAiEditingLoading(true);
    setIsAiModalOpen(false);
    setLastAiInstruction(instruction);

    try {
      const token = await getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const editPromises = targets.map(block => 
        fetch(`${API_BASE_URL}/articles/${articleId}/ai-edit`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            content: `<${block.type}>${block.content}</${block.type}>`,
            instruction
          })
        }).then(res => {
          if (!res.ok) throw new Error(`API Error on block ${block.id}`);
          return res.json();
        }).then(data => {
          const newHtml = data.new_content as string;
          const regex = new RegExp(`^<${block.type}[^>]*>([\\s\\S]*)<\\/${block.type}>$`, 'i');
          const match = newHtml.match(regex);
          const inner = match ? match[1] : newHtml;
          return {
            blockId: block.id,
            originalType: block.type,
            originalContent: block.content,
            newContent: inner,
          };
        })
      );

      const newConfirmations = await Promise.all(editPromises);
      
      setAiConfirmations(prev => {
        const updatedConfirmations = prev.filter(p => !newConfirmations.some(n => n.blockId === p.blockId));
        return [...updatedConfirmations, ...newConfirmations];
      });

    } catch (e: any) {
      alert(`AI編集に失敗しました: ${e.message}`);
    } finally {
      setAiEditingLoading(false);
    }
  };

  const handleRegenerate = async (blockId: string) => {
    const confirmation = aiConfirmations.find(c => c.blockId === blockId);
    const instruction = lastAiInstruction; 
    if (!confirmation || !instruction) return;

    setAiEditingLoading(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      
      const resp = await fetch(`${API_BASE_URL}/articles/${articleId}/ai-edit`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          content: `<${confirmation.originalType}>${confirmation.originalContent}</${confirmation.originalType}>`,
          instruction
        })
      });
      if (!resp.ok) throw new Error(`API Error: ${resp.statusText}`);
      
      const data = await resp.json();
      const newHtml = data.new_content as string;
      const regex = new RegExp(`^<${confirmation.originalType}[^>]*>([\\s\\S]*)<\\/${confirmation.originalType}>$`, 'i');
      const match = newHtml.match(regex);
      const inner = match ? match[1] : newHtml;

      setAiConfirmations(prev => prev.map(c => 
          c.blockId === blockId ? { ...c, newContent: inner } : c
      ));

    } catch (e:any) {
      alert(`AI再生成に失敗しました: ${e.message}`);
    } finally {
      setAiEditingLoading(false);
    }
  };

  const handleApprove = (blockId: string) => {
    const confirmation = aiConfirmations.find(c => c.blockId === blockId);
    if (!confirmation) return;
    saveBlock(confirmation.blockId, confirmation.newContent);
    setAiConfirmations(prev => prev.filter(c => c.blockId !== blockId));
  };
  
  const handleCancel = (blockId: string) => {
    setAiConfirmations(prev => prev.filter(c => c.blockId !== blockId));
  };
  
  const handleApproveAll = () => {
    setBlocks(prev => {
      const newBlocks = [...prev];
      aiConfirmations.forEach(conf => {
        const blockIndex = newBlocks.findIndex(b => b.id === conf.blockId);
        if (blockIndex > -1) {
          newBlocks[blockIndex].content = conf.newContent;
        }
      });
      return newBlocks;
    });
    setAiConfirmations([]);
  };

  const handleCancelAll = () => {
    setAiConfirmations([]);
  };

  // 画像アップロード処理
  const handleImageUpload = async (blockId: string, file: File) => {
    const block = blocks.find(b => b.id === blockId);
    if (!block || !block.placeholderData) return;

    try {
      setImageUploadLoading(prev => ({ ...prev, [blockId]: true }));

      const token = await getToken();
      const formData = new FormData();
      formData.append('file', file);
      formData.append('placeholder_id', block.placeholderData.placeholder_id);
      formData.append('alt_text', block.placeholderData.alt_text || block.placeholderData.description_jp);

      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/images/upload`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const result = await response.json();
      
      // プレースホルダーを実際の画像タグに置換
      const imageHtml = `<img src="${result.image_url}" alt="${block.placeholderData.alt_text || block.placeholderData.description_jp}" class="article-image" />`;
      
      setBlocks(prev => prev.map(b => 
        b.id === blockId 
          ? { ...b, type: 'p', content: imageHtml, placeholderData: undefined }
          : b
      ));

      alert('画像がアップロードされました！');
    } catch (error) {
      console.error('画像アップロードエラー:', error);
      alert('画像のアップロードに失敗しました。');
    } finally {
      setImageUploadLoading(prev => ({ ...prev, [blockId]: false }));
    }
  };

  // 画像生成処理
  const handleImageGeneration = async (blockId: string) => {
    const block = blocks.find(b => b.id === blockId);
    if (!block || !block.placeholderData) return;

    try {
      setImageGenerationLoading(prev => ({ ...prev, [blockId]: true }));

      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/images/generate`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          placeholder_id: block.placeholderData.placeholder_id,
          description_jp: block.placeholderData.description_jp,
          prompt_en: block.placeholderData.prompt_en,
        }),
      });

      if (!response.ok) {
        throw new Error(`Generation failed: ${response.status}`);
      }

      const result = await response.json();
      
      // プレースホルダーを実際の画像タグに置換
      const imageHtml = `<img src="${result.image_url}" alt="${block.placeholderData.alt_text || block.placeholderData.description_jp}" class="article-image" />`;
      
      setBlocks(prev => prev.map(b => 
        b.id === blockId 
          ? { ...b, type: 'p', content: imageHtml, placeholderData: undefined }
          : b
      ));

      alert('画像が生成されました！');
    } catch (error) {
      console.error('画像生成エラー:', error);
      alert('画像の生成に失敗しました。');
    } finally {
      setImageGenerationLoading(prev => ({ ...prev, [blockId]: false }));
    }
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

      const response = await fetch(`${API_BASE_URL}/articles/${articleId}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({
          content: updatedContent,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 成功時は記事データを再取得
      await refetch();
      alert('記事が正常に保存されました！');
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : '保存に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  // タグタイプに応じたスタイルクラス
  const getBlockStyles = (type: string) => {
    switch (type) {
      case 'h1': return 'text-3xl font-bold text-gray-900 mb-4';
      case 'h2': return 'text-2xl font-semibold text-gray-800 mb-3';
      case 'h3': return 'text-xl font-medium text-gray-700 mb-2';
      case 'p': return 'text-gray-700 mb-4 leading-relaxed';
      case 'ul': return 'list-disc list-inside text-gray-700 mb-4';
      case 'ol': return 'list-decimal list-inside text-gray-700 mb-4';
      case 'image_placeholder': return 'border-2 border-dashed border-blue-300 bg-blue-50 rounded-lg p-6 mb-4';
      default: return 'text-gray-700 mb-2';
    }
  };

  // ブロックコンテンツのレンダリング（void要素対応）
  const renderBlockContent = (block: ArticleBlock) => {
    const tagName = block.type;
    const className = getBlockStyles(block.type);
    
    // void要素の場合はdangerouslySetInnerHTMLを使わない
    if (isVoidElement(tagName)) {
      return React.createElement(tagName, { 
        className,
        key: block.id
      });
    }
    
    // 通常の要素
    return React.createElement(tagName, {
      className,
      dangerouslySetInnerHTML: { __html: block.content },
      key: block.id
    });
  };

  // 画像プレースホルダーブロックのレンダリング
  const renderImagePlaceholderBlock = (block: ArticleBlock) => {
    if (!block.placeholderData) return null;

    return (
      <div className={getBlockStyles('image_placeholder')}>
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
        <div className="max-w-4xl mx-auto space-y-2">
          {blocks.map((block) => {
            const confirmationForBlock = aiConfirmations.find(c => c.blockId === block.id);
            return (
            <div 
              key={block.id}
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
                        <div 
                          className="text-sm border p-3 rounded-md bg-gray-50 max-h-48 overflow-y-auto"
                          dangerouslySetInnerHTML={{ __html: confirmationForBlock.originalContent }}
                        />
                      </div>
                      <div>
                        <h4 className="font-bold mb-2 text-sm text-blue-600">変更後</h4>
                        <div 
                          className="text-sm border border-blue-200 p-3 rounded-md bg-blue-50 max-h-48 overflow-y-auto"
                          dangerouslySetInnerHTML={{ __html: confirmationForBlock.newContent }}
                        />
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
            );
          })}
        </div>
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
    </div>
  );
} 