'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle,Bot, Check, Loader2, RotateCcw, Save, Send, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { useAgentChat } from '@/hooks/useAgentChat';

import ArticlePreviewStyles from '../../new-article/component/ArticlePreviewStyles';

interface AIAgentEditTabProps {
  articleId: string;
  onSave?: () => void;
}

export default function AIAgentEditTab({ articleId, onSave }: AIAgentEditTabProps) {
  const {
    messages,
    loading,
    error,
    sessionId,
    createSession,
    sendMessage,
    getCurrentContent,
    getDiff,
    saveChanges,
    discardChanges,
    closeSession,
  } = useAgentChat(articleId);

  const { toast } = useToast();
  const [userInput, setUserInput] = useState('');
  const [previewContent, setPreviewContent] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // セッション作成（マウント時のみ）
  useEffect(() => {
    let mounted = true;

    const initSession = async () => {
      if (!sessionId && mounted) {
        try {
          await createSession(articleId);
        } catch (err: any) {
          if (mounted) {
            toast({
              title: 'エラー',
              description: `セッションの作成に失敗しました: ${err.message}`,
              variant: 'destructive',
            });
          }
        }
      }
    };

    initSession();

    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // アンマウント時のクリーンアップ
  useEffect(() => {
    return () => {
      if (sessionId) {
        closeSession();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // セッション作成後の初期プレビュー読み込み
  useEffect(() => {
    const loadInitialPreview = async () => {
      if (sessionId && messages.length === 0) {
        try {
          const content = await getCurrentContent();
          setPreviewContent(content);
        } catch (err) {
          console.error('Failed to load initial preview:', err);
        }
      }
    };

    loadInitialPreview();
  }, [sessionId, getCurrentContent, messages.length]);

  // メッセージ自動スクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // コンテンツ更新
  const refreshPreview = useCallback(async () => {
    if (!sessionId) return;

    try {
      const content = await getCurrentContent();
      setPreviewContent(content);

      // getDiffは編集後のみ有効なので、エラーは無視
      try {
        const diff = await getDiff();
        setHasChanges(diff.has_changes);
      } catch (diffErr) {
        // 初期状態やまだ編集がない場合はdiffエラーを無視
        setHasChanges(false);
      }
    } catch (err) {
      console.error('Failed to refresh preview:', err);
    }
  }, [sessionId, getCurrentContent, getDiff]);

  // メッセージ送信後にプレビュー更新
  useEffect(() => {
    if (sessionId && messages.length > 0) {
      refreshPreview();
    }
  }, [messages, sessionId, refreshPreview]);

  const handleSendMessage = async () => {
    if (!userInput.trim() || loading) return;

    const message = userInput;
    setUserInput('');

    try {
      await sendMessage(message);
    } catch (err) {
      toast({
        title: 'エラー',
        description: `メッセージの送信に失敗しました`,
        variant: 'destructive',
      });
    }
  };

  const handleSave = async () => {
    try {
      await saveChanges();
      toast({
        title: '成功',
        description: '変更を保存しました',
      });
      setHasChanges(false);
      onSave?.();
    } catch (err) {
      toast({
        title: 'エラー',
        description: '保存に失敗しました',
        variant: 'destructive',
      });
    }
  };

  const handleDiscard = async () => {
    try {
      await discardChanges();
      await refreshPreview();
      toast({
        title: '成功',
        description: '変更を破棄しました',
      });
      setHasChanges(false);
    } catch (err) {
      toast({
        title: 'エラー',
        description: '破棄に失敗しました',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="flex h-[calc(100vh-200px)] gap-4">
      {/* 左側: 記事プレビュー */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">記事プレビュー</h3>
          {hasChanges && (
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleDiscard}>
                <RotateCcw className="h-4 w-4 mr-1" />
                変更を破棄
              </Button>
              <Button size="sm" onClick={handleSave}>
                <Save className="h-4 w-4 mr-1" />
                変更を保存
              </Button>
            </div>
          )}
        </div>

        <Card className="flex-1 p-6 overflow-auto">
          <ArticlePreviewStyles>
            <div dangerouslySetInnerHTML={{ __html: previewContent }} />
          </ArticlePreviewStyles>
        </Card>
      </div>

      {/* 右側: チャット */}
      <div className="w-[500px] flex flex-col">
        <div className="flex items-center gap-2 mb-4">
          <Bot className="h-6 w-6 text-blue-600" />
          <h3 className="text-lg font-semibold">AIエージェント編集</h3>
        </div>

        <Card className="flex-1 flex flex-col">
          {/* メッセージエリア */}
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg p-3">
                    <Loader2 className="h-5 w-5 animate-spin text-gray-600" />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* 入力エリア */}
          <div className="border-t p-4">
            {error && (
              <div className="flex items-center gap-2 text-sm text-red-600 mb-2">
                <AlertCircle className="h-4 w-4" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex gap-2">
              <Textarea
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="例: 「この見出しをもっと分かりやすくして」「誤字脱字をチェックして」"
                className="flex-1 min-h-[60px] resize-none"
                disabled={loading || !sessionId}
              />
              <Button
                onClick={handleSendMessage}
                disabled={loading || !userInput.trim() || !sessionId}
                className="self-end"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>

            <div className="text-xs text-gray-500 mt-2">
              Shift+Enter で改行、Enter で送信
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
