'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { Container } from '@/components/container';
import { ArticleEditPage } from '@/features/article-editing/components/article-edit-page';
import { GeneratedArticle } from '@/features/article-generation/types';

export default function EditArticlePage() {
  const router = useRouter();
  const [article, setArticle] = useState<GeneratedArticle | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // 記事データをローカルストレージから取得
    const articleData = localStorage.getItem('draftArticle');
    if (articleData) {
      try {
        const parsedArticle = JSON.parse(articleData) as GeneratedArticle;
        setArticle(parsedArticle);
      } catch (error) {
        console.error('Failed to parse article data:', error);
      }
    } else {
      // 記事がない場合は生成ページにリダイレクト
      router.push('/generate');
    }
    setIsLoading(false);
  }, [router]);

  const handleSaveArticle = async (updatedArticle: GeneratedArticle) => {
    // 本番環境では、ここでAPIを呼び出して記事を保存
    // 現在はローカルストレージに保存
    localStorage.setItem('draftArticle', JSON.stringify(updatedArticle));
    // 保存後にURLパラメータを更新するなどの処理を追加できる
    return Promise.resolve();
  };

  // ローディング中の表示
  if (isLoading) {
    return (
      <Container className="py-10">
        <div className="flex min-h-[300px] items-center justify-center">
          <div className="text-center">
            <p className="text-xl">記事データを読み込み中...</p>
            <div className="mt-4 h-2 w-32 animate-pulse rounded-full bg-indigo-500"></div>
          </div>
        </div>
      </Container>
    );
  }

  // 記事データがない場合
  if (!article) {
    return (
      <Container className="py-10">
        <div className="flex min-h-[300px] items-center justify-center">
          <div className="text-center">
            <p className="text-xl text-red-500">記事データが見つかりませんでした。</p>
            <p className="mt-2">
              <button
                onClick={() => router.push('/generate')}
                className="underline hover:text-indigo-500"
              >
                記事生成ページに戻る
              </button>
            </p>
          </div>
        </div>
      </Container>
    );
  }

  return (
    <Container className="py-10">
      <ArticleEditPage article={article} onSave={handleSaveArticle} />
    </Container>
  );
}
