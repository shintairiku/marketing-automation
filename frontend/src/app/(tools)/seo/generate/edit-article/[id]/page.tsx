'use client';

import { use } from 'react';

import Header from '@/components/display/header';
import Sidebar from '@/components/display/sidebar';
import EditArticlePage from '@/features/tools/seo/generate/edit-article/EditArticlePage';

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <div className="min-h-screen bg-[#eeeeee]">
      <Header />
      <div className="flex mt-[45px]">
        <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)]">
          <Sidebar />
        </div>
        <main className="flex-1 ml-[314px] p-5">
          <EditArticlePage articleId={id} />
        </main>
      </div>
    </div>
  );
} 