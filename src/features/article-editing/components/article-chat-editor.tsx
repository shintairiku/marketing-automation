'use client';

import { useEffect, useRef, useState } from 'react';
import { IoSend } from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/components/ui/use-toast';
import { ChatMessage } from '@/features/article-editing/types';
import { GeneratedArticle } from '@/features/article-generation/types';

interface ArticleChatEditorProps {
  article: GeneratedArticle;
  onArticleUpdate: (updatedArticle: GeneratedArticle) => void;
}

export function ArticleChatEditor({ article, onArticleUpdate }: ArticleChatEditorProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'system-1',
      role: 'system',
      content: '記事の編集を開始しました。どのように記事を修正しますか？',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // チャットを下までスクロール
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }

    if (!inputMessage.trim()) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // ここではモックレスポンスを使用。本番ではLLM APIを呼び出す
      // このようなモックは開発時のみ使用し、実際の実装ではバックエンドAPIを呼び出す
      await simulateApiCall(userMessage.content, article);
    } catch (error) {
      toast({
        variant: 'destructive',
        description: 'AIとの通信中にエラーが発生しました。もう一度お試しください。',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // モックAPIコール（開発用）
  const simulateApiCall = async (message: string, currentArticle: GeneratedArticle) => {
    // 実際のアプリケーションでは、ここでLLM APIを呼び出す
    await new Promise((resolve) => setTimeout(resolve, 1500)); // 応答時間をシミュレート

    // デモ用の応答を生成
    let responseContent = '';
    let updatedArticle = { ...currentArticle };

    if (message.toLowerCase().includes('タイトル')) {
      responseContent = `タイトルを修正しました。以下が更新後のタイトルです：\n\n「${currentArticle.title}の効果的な活用法」\n\n他に修正したい箇所はありますか？`;
      updatedArticle = {
        ...updatedArticle,
        title: `${currentArticle.title}の効果的な活用法`,
      };
    } else if (message.toLowerCase().includes('導入')) {
      const introSection = updatedArticle.sections.find((s) => s.level === 'h2' && s.id === updatedArticle.sections[0].id);
      if (introSection) {
        responseContent = `導入部分を修正しました。より興味を引くように書き直しています。`;
        updatedArticle = {
          ...updatedArticle,
          sections: updatedArticle.sections.map((section) =>
            section.id === introSection.id
              ? {
                  ...section,
                  content:
                    '多くの人がこのトピックについて知りたいと思っているでしょう。本記事では、専門家の視点から詳しく解説し、実践的なアドバイスをお届けします。\n\n最近の調査によると、このトピックへの関心は年々高まっており、その重要性は今後さらに増していくと予想されています。',
                }
              : section
          ),
        };
      } else {
        responseContent = `導入部分が見つかりませんでした。最初のセクションに導入を追加しますか？`;
      }
    } else if (message.toLowerCase().includes('簡潔に') || message.toLowerCase().includes('短く')) {
      responseContent = `記事全体をより簡潔にまとめました。不要な冗長表現を削除し、ポイントを明確にしています。`;
      // 実際には全セクションの内容を短くするロジックが入る
    } else {
      responseContent = `ご指示ありがとうございます。何か具体的な修正点があればお知らせください。例えば：\n\n- タイトルの変更\n- 特定のセクションの追加・削除\n- 文章の簡潔化\n- 専門用語の説明追加\n- 事例やデータの追加`;
    }

    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: responseContent,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, assistantMessage]);
    onArticleUpdate(updatedArticle);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto rounded-t-md border border-gray-700 bg-black p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-3/4 rounded-lg px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-indigo-900 text-white'
                    : message.role === 'system'
                    ? 'bg-gray-800 text-gray-300'
                    : 'bg-gray-700 text-white'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                <div className="mt-1 text-right text-xs text-gray-400">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>
      </div>

      <div className="border-t border-gray-700 bg-black p-4">
        <form onSubmit={handleSendMessage} className="flex items-end gap-2">
          <Textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="記事の修正指示を入力してください..."
            className="flex-1 resize-none"
            rows={2}
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
          />
          <Button
            type="submit"
            size="icon"
            variant="secondary"
            className="h-10 w-10"
            disabled={isLoading || !inputMessage.trim()}
          >
            <IoSend size={18} />
          </Button>
        </form>
      </div>
    </div>
  );
}
