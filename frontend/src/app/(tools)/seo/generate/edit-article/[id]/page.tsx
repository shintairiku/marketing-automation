import EditArticlePage from '@/features/tools/seo/generate/edit-article/EditArticlePage';

interface PageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function Page({ params }: PageProps) {
  const { id } = await params;
  
  return <EditArticlePage articleId={id} />;
} 